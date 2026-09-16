import Foundation

/// Kesalahan yang dilempar saat berinteraksi dengan engine Python.
enum EngineError: LocalizedError {
    case engineNotFound(String)
    case cliError(String)
    case badOutput(String)

    var errorDescription: String? {
        switch self {
        case .engineNotFound(let p):
            return "Engine runtime tidak ditemukan: \(p)"
        case .cliError(let m):
            return "Error engine: \(m)"
        case .badOutput(let m):
            return "Output engine tidak valid: \(m)"
        }
    }
}

/// Proses engine Python yang PERSISTEN (daemon).
///
/// Alih-alih mem-boot PyInstaller baru setiap operasi (~1-2 detik karena
/// import pycalphad + matplotlib), engine dijalankan SEKALI dalam mode
/// `--daemon`. Klien mengirim satu baris JSON `{"id","cmd","args"}` lewat
/// stdin; engine memproses dengan ThreadPoolExecutor (memakai semua core)
/// dan membalas satu baris JSON `{"id","ok",...}` per permintaan (boleh
/// out-of-order, dipasangkan lewat id yang sama).
final class EngineDaemon {
    private let executable: String
    private let devScript: String   // kosong saat mode bundled
    private let process = Process()
    private let stdinPipe = Pipe()
    private let stdoutPipe = Pipe()
    private let lock = NSLock()
    private let writerLock = NSLock()
    private var nextID = 1
    private var pending: [Int: (Result<[String: Any], Error>) -> Void] = [:]
    private var started = false
    private var usable = true
    private var stdoutBuffer = Data()   // buffer antar-chunk utk baris utuh
    private let bufferLock = NSLock()

    init(executable: String, devScript: String = "") {
        self.executable = executable
        self.devScript = devScript
    }

    var isUsable: Bool { usable }

    /// Memulai proses daemon (idempotent). Melempar bila gagal start.
    private func start() throws {
        lock.lock()
        defer { lock.unlock() }
        guard !started else { return }
        process.standardOutput = stdoutPipe
        if let errPath = ProcessInfo.processInfo.environment["THERMOAPP_DAEMON_ERR"] {
            try? FileManager.default.createFile(atPath: errPath, contents: nil)
            process.standardError = try? FileHandle(forWritingTo: URL(fileURLWithPath: errPath))
            // fallback: bila gagal buat file, jangan crash
            if process.standardError == nil { process.standardError = FileHandle.nullDevice }
        } else {
            process.standardError = FileHandle.nullDevice
        }
        process.standardInput = stdinPipe

        if devScript.isEmpty {
            process.executableURL = URL(fileURLWithPath: executable)
            process.arguments = ["--daemon"]
        } else {
            process.executableURL = URL(fileURLWithPath: executable)
            process.arguments = [devScript, "--daemon"]
        }
        try process.run()

        // Pembaca stdout: satu-satunya thread yang membaca; memanggil handler
        // sesuai id (boleh keluar tidak berurutan).
        // PENTING: availableData bisa memecah satu baris JSON — jadi baris
        // ditumpuk di buffer dan hanya baris yang diakhiri '\n' diproses.
        stdoutPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            guard let self = self else { return }
            let chunk = handle.availableData
            if chunk.isEmpty {
                self.stdoutBuffer = Data()
                self.terminate()
                return
            }
            // pelindung akses buffering
            self.bufferLock.lock()
            self.stdoutBuffer.append(chunk)
            var lines: [String] = []
            while let nl = self.stdoutBuffer.firstIndex(of: 0x0A) {
                let lineData = self.stdoutBuffer.subdata(in: self.stdoutBuffer.startIndex..<nl)
                self.stdoutBuffer.removeSubrange(self.stdoutBuffer.startIndex...nl)
                if let s = String(data: lineData, encoding: .utf8), !s.isEmpty {
                    lines.append(s)
                }
            }
            self.bufferLock.unlock()
            for line in lines { self.handle(line: line) }
        }
        started = true
    }

    /// Parse satu baris balasan dan memanggil handler yang cocok.
    private func handle(line: String) {
        guard let data = line.data(using: .utf8),
              let obj = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] else {
            return
        }
        guard let rawID = obj["id"] else { return }
        let id: Int
        if let n = rawID as? NSNumber { id = n.intValue }
        else if let i = rawID as? Int { id = i }
        else { return }
        lock.lock()
        let handler = pending.removeValue(forKey: id)
        lock.unlock()
        guard let handler = handler else { return }
        if let ok = obj["ok"] as? Bool, ok == false {
            let msg = obj["error"] as? String ?? "engine error"
            handler(.failure(EngineError.cliError(msg)))
        } else {
            handler(.success(obj))
        }
    }

    /// Mengirim satu permintaan dan MENUNGGU balasan yang cocok (sinkron).
    func send(cmd: String, args: [String: Any]) throws -> [String: Any] {
        try start()
        let id: Int = {
            writerLock.lock()
            defer { writerLock.unlock() }
            let i = nextID
            nextID += 1
            return i
        }()

        let req: [String: Any] = ["id": id, "cmd": cmd, "args": args]
        let payload = try jsonData(from: req) + "\n"
        guard let data = payload.data(using: .utf8) else {
            throw EngineError.badOutput("Gagal encode request.")
        }

        writerLock.lock()
        stdinPipe.fileHandleForWriting.write(data)
        // CATATAN: jangan panggil synchronizeFile() pada pipe — itu melempar
        // ObjC exception (SIGABRT). Pipe bukan file.
        writerLock.unlock()

        let sem = DispatchSemaphore(value: 0)
        var result: Result<[String: Any], Error>?
        lock.lock()
        pending[id] = { r in result = r; sem.signal() }
        lock.unlock()

        // Batas waktu supaya tidak menggantung UI bila engine macet.
        let waited = sem.wait(timeout: .now() + 120)
        if waited == .timedOut {
            lock.lock()
            pending.removeValue(forKey: id)
            lock.unlock()
            throw EngineError.cliError("Engine tidak menjawab (timeout).")
        }
        guard let r = result else {
            throw EngineError.cliError("Engine tidak mengembalikan hasil.")
        }
        return try r.get()
    }

    /// Hentikan proses dan gagalkan semua permintaan tertunda.
    func terminate() {
        lock.lock()
        let stuck = Array(pending.values)
        pending.removeAll()
        usable = false
        lock.unlock()
        for h in stuck { h(.failure(EngineError.cliError("Engine terhenti."))) }
        if process.isRunning { process.terminate() }
    }

    deinit { terminate() }

    private func jsonData(from obj: Any) throws -> String {
        let data = try JSONSerialization.data(withJSONObject: obj)
        guard let s = String(data: data, encoding: .utf8) else {
            throw EngineError.badOutput("Gagal encode JSON.")
        }
        return s
    }
}

/// Jembatan ke mesin perhitungan Python (pycalphad).
///
/// Dua mode:
///  - **Bundled (produksi):** memanggil binary mandiri `engine_runner`
///    (PyInstaller) di `Contents/Resources/`, dijalankan sekali sebagai daemon.
///  - **Development:** memanggil `engine_cli.py` via venv, juga sebagai daemon.
final class EngineBridge {
    /// Path executable engine (binary mandiri) atau "" bila tak dibundel.
    private let bundledExecutable: String

    /// Path ke `engine_cli.py` (mode dev).
    private let scriptPath: String

    /// Daemon persisten (lazy). Nil bila gagal start -> fallback one-shot.
    private var daemon: EngineDaemon?
    private let daemonLock = NSLock()

    init(bundledExecutable: String? = nil, scriptPath: String? = nil) {
        if let be = bundledExecutable, !be.isEmpty {
            self.bundledExecutable = be
            self.scriptPath = ""
        } else {
            self.bundledExecutable = ""
            self.scriptPath = scriptPath ?? Self.defaultScriptPath()
        }
    }

    /// Menemukan engine yang dibundel dalam .app, atau "" bila tidak ada.
    static func bundledEnginePath() -> String {
        if let p = Bundle.main.path(forResource: "engine_runner", ofType: nil,
                                    inDirectory: nil) {
            return p
        }
        return ""
    }

    static func defaultScriptPath() -> String {
        let projectRoot = URL(fileURLWithPath: #file)
            .deletingLastPathComponent()   // native
            .deletingLastPathComponent()   // thermoapp
        return projectRoot.appendingPathComponent("engine_cli.py").path
    }

    private func pythonPath() -> String {
        let cwd = URL(fileURLWithPath: scriptPath).deletingLastPathComponent()
        let venv = cwd.appendingPathComponent(".venv/bin/python3")
        if FileManager.default.isExecutableFile(atPath: venv.path) {
            return venv.path
        }
        return "/usr/bin/python3"
    }

    /// Mengubah argv `["cmd","--k","v",...]` menjadi dict `{"k": v,...}`
    /// yang sesuai protokol daemon (nilai yang bisa di-parse JSON dikirim
    /// sebagai objek; sisanya sebagai string).
    private func argvToDict(_ argv: [String]) -> [String: Any] {
        var dict: [String: Any] = [:]
        var i = 1
        while i < argv.count {
            let tok = argv[i]
            if tok.hasPrefix("--"), i + 1 < argv.count {
                let key = String(tok.dropFirst(2))
                let raw = argv[i + 1]
                if let d = raw.data(using: .utf8),
                   let obj = try? JSONSerialization.jsonObject(with: d) {
                    dict[key] = obj
                } else {
                    dict[key] = raw
                }
                i += 2
            } else {
                i += 1
            }
        }
        return dict
    }

    /// Menjalankan perintah engine; mengembalikan stdout JSON.
    ///
    /// Diprioritaskan lewat daemon persisten (cepat). Bila daemon gagal,
    /// jatuh ke mode one-shot (spawn proses sekali) sebagai pengaman.
    private func run(arguments: [String]) throws -> String {
        if let d = daemon, d.isUsable {
            let cmd = arguments.first ?? ""
            let args = argvToDict(arguments)
            let resp = try d.send(cmd: cmd, args: args)
            return try jsonString(fromDict: resp)
        }

        // Fallback one-shot bila daemon tidak tersedia
        daemonLock.lock()
        defer { daemonLock.unlock() }
        if daemon == nil {
            // coba buat daemon; gagal -> lanjut one-shot
            do {
                if !bundledExecutable.isEmpty {
                    _dbg("run(): creating daemon for bundled exe")
                    let d = EngineDaemon(executable: bundledExecutable)
                    _ = try d.send(cmd: "databases", args: [:])
                    _dbg("run(): daemon adopted after databases test")
                    daemon = d
                } else {
                    _dbg("run(): creating daemon for dev script")
                    let d = EngineDaemon(executable: pythonPath(), devScript: scriptPath)
                    _ = try d.send(cmd: "databases", args: [:])
                    _dbg("run(): dev daemon adopted")
                    daemon = d
                }
            } catch {
                _dbg("run(): daemon creation FAILED: \(error)")
                daemon = nil
            }
        }
        if let d = daemon, d.isUsable {
            let cmd = arguments.first ?? ""
            let args = argvToDict(arguments)
            let resp = try d.send(cmd: cmd, args: args)
            return try jsonString(fromDict: resp)
        }

        // Jalan terakhir: proses one-shot seperti sebelumnya
        return try runOneShot(arguments: arguments)
    }

    private func runOneShot(arguments: [String]) throws -> String {
        let process = Process()
        let outPipe = Pipe()
        let errPipe = Pipe()
        process.standardOutput = outPipe
        process.standardError = errPipe
        if !bundledExecutable.isEmpty {
            process.executableURL = URL(fileURLWithPath: bundledExecutable)
            process.arguments = arguments
        } else {
            process.executableURL = URL(fileURLWithPath: pythonPath())
            process.arguments = [scriptPath] + arguments
        }
        try process.run()
        let outData = outPipe.fileHandleForReading.readDataToEndOfFile()
        let errData = errPipe.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()
        guard process.terminationStatus == 0 else {
            let err = String(data: errData, encoding: .utf8) ?? ""
            throw EngineError.cliError("Kode keluar \(process.terminationStatus): \(err)")
        }
        guard let output = String(data: outData, encoding: .utf8) else {
            throw EngineError.badOutput("Tidak dapat membaca output.")
        }
        return output
    }

    private func parseJSON(_ output: String) throws -> [String: Any] {
        let trimmed = output.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let data = trimmed.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            throw EngineError.badOutput(output)
        }
        if let err = obj["error"] as? String {
            throw EngineError.cliError(err)
        }
        return obj
    }

    // MARK: - API

    func databases() throws -> [[String: Any]] {
        let out = try run(arguments: ["databases"])
        let obj = try parseJSON(out)
        return obj["databases"] as? [[String: Any]] ?? []
    }

    /// Label reaksi oksidasi/reduktor untuk Ellingham + daftar spesies reaksi.
    func labels() throws -> (oxidation: [String], reductants: [String], species: [String]) {
        let out = try run(arguments: ["labels"])
        let obj = try parseJSON(out)
        return (
            obj["oxidation"] as? [String] ?? [],
            obj["reductants"] as? [String] ?? [],
            obj["species"] as? [String] ?? []
        )
    }

    func equilibrium(db: String, comp: [String: Double], T: Double, P: Double = 101325.0) throws -> [String: Any] {
        let compJSON = try jsonString(from: comp)
        let out = try run(arguments: [
            "equilibrium", "--db", db, "--comp", compJSON, "--T", String(T), "--P", String(P),
        ])
        return try parseJSON(out)
    }

    func reaction(reactants: [String], products: [String], T: Double) throws -> [String: Any] {
        let rJSON = try jsonString(from: reactants)
        let pJSON = try jsonString(from: products)
        let out = try run(arguments: [
            "reaction", "--reactants", rJSON, "--products", pJSON, "--T", String(T),
        ])
        return try parseJSON(out)
    }

    func phaseDiagram(db: String, A: String, B: String,
                      tmin: Double, tmax: Double, nx: Int,
                      outPath: String) throws -> String {
        let out = try run(arguments: [
            "phasediagram", "--db", db, "--A", A, "--B", B,
            "--tmin", String(tmin), "--tmax", String(tmax), "--nx", String(nx),
            "--out", outPath,
        ])
        let obj = try parseJSON(out)
        guard let file = obj["file"] as? String else {
            throw EngineError.badOutput("phasediagram tidak mengembalikan file.")
        }
        return file
    }

    /// Helper: jalankan subcommand yang menulis PNG ke file, kembalikan path.
    private func renderToFile(arguments: [String]) throws -> String {
        let out = try run(arguments: arguments)
        let obj = try parseJSON(out)
        guard let file = obj["file"] as? String else {
            throw EngineError.badOutput("Subcommand tidak mengembalikan file.")
        }
        return file
    }

    /// Diagram Ellingham (ΔG vs T oksidasi/redoks).
    func ellingham(oxids: [String], reductants: [String]?,
                   tmin: Double, tmax: Double, outPath: String) throws -> String {
        var args = ["ellingham", "--oxids", try jsonString(from: oxids)]
        if let r = reductants, !r.isEmpty {
            args += ["--reductants", try jsonString(from: r)]
        }
        args += ["--tmin", String(tmin), "--tmax", String(tmax), "--out", outPath]
        return try renderToFile(arguments: args)
    }

    /// Diagram TTT baja karbon.
    func ttt(c: Double, mn: Double, cr: Double, mo: Double, si: Double?,
             outPath: String) throws -> String {
        var args = ["ttt", "--c", String(c), "--mn", String(mn),
                    "--cr", String(cr), "--mo", String(mo)]
        if let s = si {
            args += ["--si", String(s)]
        }
        args += ["--out", outPath]
        return try renderToFile(arguments: args)
    }

    /// Plot ΔG vs T (stabilitas senyawa).
    func gibbs(categories: [String]?, tmin: Double, tmax: Double,
               outPath: String) throws -> String {
        var args = ["gibbs"]
        if let cats = categories {
            args += ["--categories", try jsonString(from: cats)]
        }
        args += ["--tmin", String(tmin), "--tmax", String(tmax), "--out", outPath]
        return try renderToFile(arguments: args)
    }

    /// Diagram Pourbaix (E-pH, Fe-H2O).
    func pourbaix(outPath: String) throws -> String {
        return try renderToFile(arguments: ["pourbaix", "--out", outPath])
    }

    private func jsonString<T: Encodable>(from value: T) throws -> String {
        let data = try JSONEncoder().encode(value)
        guard let s = String(data: data, encoding: .utf8) else {
            throw EngineError.badOutput("Tidak dapat meng-encode JSON.")
        }
        return s
    }

    /// Encode dict (hasil daemon) menjadi string JSON untuk di-parse ulang.
    private func jsonString(fromDict value: [String: Any]) throws -> String {
        let data = try JSONSerialization.data(withJSONObject: value)
        guard let s = String(data: data, encoding: .utf8) else {
            throw EngineError.badOutput("Tidak dapat meng-encode JSON.")
        }
        return s
    }
}
