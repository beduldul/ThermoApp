import Foundation
import SwiftUI

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
            self.bridge = EngineBridge(bundledExecutable: be)
        } else {
            self.bridge = EngineBridge(scriptPath: scriptPath)
        }
        refreshDatabases()
    }

    func refreshDatabases() {
        do {
            let raw = try bridge.databases()
            DispatchQueue.main.async {
                self.databases = raw.compactMap { DatabaseInfo($0) }
            }
        } catch {
            DispatchQueue.main.async {
                self.databases = []
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
