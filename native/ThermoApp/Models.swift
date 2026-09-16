import Foundation
import SwiftUI

/// Diagnostik: tulis baris ke file bila env THERMOAPP_DEBUG set.
func _dbg(_ s: String) {
    guard let p = ProcessInfo.processInfo.environment["THERMOAPP_DEBUG"] else { return }
    let line = "[\(Date())] \(s)\n"
    if let d = line.data(using: .utf8) {
        if let h = try? FileHandle(forWritingTo: URL(fileURLWithPath: p)) {
            defer { try? h.close() }
            try? h.seekToEnd()
            try? h.write(contentsOf: d)
        } else {
            try? line.write(toFile: p, atomically: true, encoding: .utf8)
        }
    }
}

/// Model hasil kesetimbangan fasa.
struct EquilibriumOutput {
    let phases: [String]
    let fractions: [Double]
    let compositions: [String: [String: Double]]
    let elements: [String]
    let gm: Double?
}

/// Model hasil reaksi.
struct ReactionOutput {
    let dg: Double
    let dh: Double
    let ds: Double
    let feasible: Bool
    let note: String
}

/// Model database CALPHAD.
struct DatabaseInfo: Identifiable, Equatable, Hashable {
    let id: String
    let label: String
    let elements: String

    init(_ dict: [String: Any]) {
        self.id = dict["id"] as? String ?? ""
        self.label = dict["label"] as? String ?? id
        self.elements = dict["elements"] as? String ?? ""
    }
}

/// Environment object pembungkus EngineBridge agar dipakai seluruh views.
final class AppModel: ObservableObject {
    let bridge: EngineBridge
    @Published var databases: [DatabaseInfo] = []

    init(scriptPath: String? = nil, bundledEngine: String? = nil) {
        let be = bundledEngine ?? EngineBridge.bundledEnginePath()
        if !be.isEmpty {
            _dbg("using BUNDLED engine: \(be)")
            self.bridge = EngineBridge(bundledExecutable: be)
        } else {
            _dbg("bundled engine NOT found; fallback script")
            self.bridge = EngineBridge(scriptPath: scriptPath)
        }
        refreshDatabases()
    }

    func refreshDatabases() {
        // JANGAN blokir thread utama: boot daemon pertama (ekstraksi PyInstaller
        // + import pycalphad + cache font matplotlib) bisa makan ~10 detik.
        // Jalankan di queue latar agar UI langsung tampil responsif, lalu
        // perbarui hasilnya di main thread.
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let raw: [[String: Any]]
            let t0 = Date()
            do {
                raw = try self?.bridge.databases() ?? []
            } catch {
                let ms = Int(Date().timeIntervalSince(t0) * 1000)
                _dbg("refreshDatabases FAILED after \(ms)ms: \(error)")
                raw = []
            }
            let ms = Int(Date().timeIntervalSince(t0) * 1000)
            _dbg("refreshDatabases got \(raw.count) DBs in \(ms)ms")
            DispatchQueue.main.async {
                self?.databases = raw.compactMap { DatabaseInfo($0) }
            }
        }
    }
}

/// Spesies termokimia yang tersedia untuk modul reaksi.
let REACTION_SPECIES: [String] = [
    "Al(s)", "Al2O3(s)", "Al(l)", "CaCO3(s)", "CaCl2(s)", "CaO(s)",
    "C(s,grafit)", "Cl2(g)", "CO(g)", "CO2(g)", "Cu(s)", "Cu2O(s)", "CuO(s)",
    "Fe(s)", "Fe(l)", "Fe2O3(s)", "Fe3O4(s)", "FeO(s)", "FeS(s)",
    "H2(g)", "H2O(g)", "H2O(l)", "Mg(s)", "MgO(s)", "N2(g)", "NaCl(s)",
    "NH3(g)", "Ni(s)", "O2(g)", "SiO2(s,quartz)", "Si(s)", "Ti(s)", "TiO2(s,ru)",
    "Zn(s)", "ZnO(s)",
]
