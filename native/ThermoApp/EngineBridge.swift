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

/// Jembatan ke mesin perhitungan Python (pycalphad).
///
/// Dua mode:
///  - **Bundled (produksi):** memanggil binary mandiri `engine_runner`
///    (buatan PyInstaller) yang diletakkan di `Contents/Resources/`.
///  - **Development:** memanggil `engine_cli.py` melalui Python venv.
final class EngineBridge {
    /// Path executable engine (binary mandiri) atau "" bila tak dibundel.
    private let bundledExecutable: String

    /// Path ke `engine_cli.py` (mode dev).
    private let scriptPath: String

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

    /// Menjalankan perintah engine dengan argumen, mengembalikan stdout.
    private func run(arguments: [String]) throws -> String {
        let process = Process()
        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        process.standardOutput = stdoutPipe
        process.standardError = stderrPipe

        if !bundledExecutable.isEmpty {
            // Mode produksi: jalankan binary mandiri langsung
            process.executableURL = URL(fileURLWithPath: bundledExecutable)
            process.arguments = arguments
        } else {
            // Mode dev: python3 script.py args
            process.executableURL = URL(fileURLWithPath: pythonPath())
            process.arguments = [scriptPath] + arguments
        }

        try process.run()
        let outData = stdoutPipe.fileHandleForReading.readDataToEndOfFile()
        let errData = stderrPipe.fileHandleForReading.readDataToEndOfFile()
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

    private func pythonPath() -> String {
        // 1. venv proyek
        let cwd = URL(fileURLWithPath: scriptPath).deletingLastPathComponent()
        let venv = cwd.appendingPathComponent(".venv/bin/python3")
        if FileManager.default.isExecutableFile(atPath: venv.path) {
            return venv.path
        }
        // 2. python3 sistem
        return "/usr/bin/python3"
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

    private func jsonString<T: Encodable>(from value: T) throws -> String {
        let data = try JSONEncoder().encode(value)
        guard let s = String(data: data, encoding: .utf8) else {
            throw EngineError.badOutput("Tidak dapat meng-encode JSON.")
        }
        return s
    }
}
