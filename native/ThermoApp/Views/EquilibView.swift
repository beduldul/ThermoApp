import SwiftUI
import UniformTypeIdentifiers

/// Modul Equilib — kesetimbangan fasa.
struct EquilibView: View {
    @EnvironmentObject var model: AppModel

    @State private var dbID: String = ""
    @State private var elements: [String] = []
    @State private var fractions: [String: Double] = [:]
    @State private var temperature: Double = 1500.0
    @State private var pressure: Double = 101325.0
    @State private var result: EquilibriumOutput?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                header("⚖️ Equilib — Kesetimbangan Fasa",
                      "Menghitung fasa setimbang via minimasi energi Gibbs (CALPHAD).")

                HStack(alignment: .top, spacing: 20) {
                    // Kolom input
                    VStack(alignment: .leading, spacing: 16) {
                        databasePicker
                        compositionEditor
                        conditionEditor
                        calculateButton
                    }
                    .frame(maxWidth: 360, alignment: .leading)

                    // Kolom hasil
                    ScrollView {
                        resultPanel
                    }
                    .frame(maxWidth: .infinity)
                }
            }
            .padding(20)
        }
        .onAppear(perform: selectDefaultDB)
        .onChange(of: model.databases) { _, _ in selectDefaultDBIfNeeded() }
    }

    // MARK: - Subviews

    private var databasePicker: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label("Daftar database", systemImage: "cylinder.split.1x2")
                .font(.headline)
            Picker("Database", selection: $dbID) {
                ForEach(model.databases) { db in
                    Text("\(db.label) — \(db.elements)").tag(db.id)
                }
            }
            .onChange(of: dbID) { _, newID in
                loadElements(for: newID)
            }
        }
    }

    private var compositionEditor: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label("Komposisi (fraksi mol)", systemImage: "slider.horizontal.3")
                .font(.headline)
            if elements.isEmpty {
                Text("Pilih database untuk melihat elemen.")
                    .font(.caption)
                    .foregroundColor(.secondary)
            } else {
                ForEach(Array(elements.enumerated()), id: \.element) { idx, el in
                    compRow(el, isLast: idx == elements.count - 1)
                }
                if elements.count > 1 {
                    let rem = remainingFraction
                    Text("Elemen terakhir otomatis = \(String(format: "%.3f", rem)) (sisa)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
    }

    private func compRow(_ el: String, isLast: Bool) -> some View {
        HStack {
            Text(el).frame(width: 40, alignment: .leading).fontWeight(.medium)
            Slider(
                value: Binding(
                    get: { fractions[el] ?? defaultFraction(for: el) },
                    set: { newVal in
                        if isLast { return }
                        fractions[el] = min(newVal, remainingExcluding(el))
                    }
                ),
                in: 0...1
            )
            .disabled(isLast && elements.count > 1)
            Text(String(format: "%.3f", fractions[el] ?? defaultFraction(for: el)))
                .font(.caption.monospacedDigit())
                .frame(width: 52, alignment: .trailing)
        }
    }

    private var conditionEditor: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Kondisi", systemImage: "thermometer.medium")
                .font(.headline)
            HStack {
                Text("Suhu (K)")
                Spacer()
                TextField("T", value: $temperature, format: .number)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 110)
            }
            HStack {
                Text("Tekanan (Pa)")
                Spacer()
                TextField("P", value: $pressure, format: .number)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 110)
            }
        }
    }

    private var calculateButton: some View {
        Button(action: runEquilibrium) {
            if isLoading {
                ProgressView().frame(maxWidth: .infinity)
            } else {
                Text("Hitung Kesetimbangan").frame(maxWidth: .infinity)
            }
        }
        .buttonStyle(.borderedProminent)
        .disabled(isLoading || dbID.isEmpty)
    }

    @ViewBuilder
    private var resultPanel: some View {
        if let err = errorMessage {
            errorBox(err)
        } else if let res = result {
            resultContent(res)
        } else {
            VStack(alignment: .leading, spacing: 8) {
                Text("Hasil akan tampil di sini.")
                    .font(.headline)
                Text(
                    "Contoh: Database Al-Ni, komposisi Al=0.5, Ni=0.5, T=1700 K → fasa LIQUID. "
                    + "T=1000 K → fasa padat AL3NI2."
                )
                .font(.caption)
                .foregroundColor(.secondary)
            }
            .padding()
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(nsColor: .controlBackgroundColor))
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }

    private func resultContent(_ res: EquilibriumOutput) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            if let gm = res.gm {
                Text("Energi Gibbs total: \(gm, specifier: "%,.1f") J/mol")
                    .font(.headline)
            }
            if res.phases.isEmpty {
                Text("Tidak ada fasa setimbang dihitung.").foregroundColor(.secondary)
            } else {
                ForEach(Array(res.phases.enumerated()), id: \.offset) { i, ph in
                    phaseCard(ph, fraction: i < res.fractions.count ? res.fractions[i] : 0,
                              comp: res.compositions[ph] ?? [:], elements: res.elements)
                }
            }
        }
    }

    private func phaseCard(_ ph: String, fraction: Double, comp: [String: Double], elements: [String]) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(ph).font(.headline)
                Spacer()
                Text("Fraksi: \(fraction, specifier: "%.4f")")
                    .font(.subheadline).foregroundColor(.secondary)
            }
            if !comp.isEmpty {
                let row = elements.map { "\($0)=\(String(format: "%.4f", comp[$0] ?? 0))" }
                Text(row.joined(separator: " · "))
                    .font(.caption.monospaced())
                    .foregroundColor(.secondary)
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(nsColor: .controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    // MARK: - Helpers

    private func header(_ title: String, _ sub: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.title.bold())
            Text(sub).font(.caption).foregroundColor(.secondary)
        }
    }

    private func errorBox(_ msg: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill").foregroundColor(.red)
            Text(msg).font(.callout)
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.red.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private func selectDefaultDB() {
        guard dbID.isEmpty, !model.databases.isEmpty else { return }
        dbID = model.databases.first?.id ?? ""
        loadElements(for: dbID)
    }

    private func selectDefaultDBIfNeeded() {
        if dbID.isEmpty && !model.databases.isEmpty {
            selectDefaultDB()
        }
    }

    private func loadElements(for id: String) {
        // Elemen diambil dari metadata database (label berisi daftar elemen).
        guard let db = model.databases.first(where: { $0.id == id }) else { return }
        let list = db.elements
            .split(separator: "-")
            .map { String($0).trimmingCharacters(in: .whitespaces) }
        elements = list
        // Inisialisasi fraksi merata
        if !list.isEmpty {
            let each = 1.0 / Double(list.count)
            fractions = Dictionary(uniqueKeysWithValues: list.map { ($0, each) })
        }
    }

    private func defaultFraction(for el: String) -> Double {
        let each = 1.0 / Double(max(elements.count, 1))
        return each
    }

    private var remainingFraction: Double {
        let others = elements.dropLast().reduce(0.0) { $0 + (fractions[$1] ?? defaultFraction(for: $1)) }
        return min(max(1.0 - others, 0.0), 1.0)
    }

    private func remainingExcluding(_ el: String) -> Double {
        let others = elements.filter { $0 != el }.reduce(0.0) {
            $0 + (fractions[$1] ?? defaultFraction(for: $1))
        }
        return min(max(1.0 - others, 0.0), 1.0)
    }

    private func runEquilibrium() {
        isLoading = true
        errorMessage = nil
        // Normalisasi fraksi
        let total = fractions.values.reduce(0.0, +)
        var comp: [String: Double] = [:]
        for el in elements {
            comp[el] = (fractions[el] ?? 0) / max(total, 1e-12)
        }
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                let raw = try model.bridge.equilibrium(db: dbID, comp: comp, T: temperature, P: pressure)
                let out = parseEquilibrium(raw)
                DispatchQueue.main.async {
                    self.result = out
                    self.isLoading = false
                }
            } catch {
                DispatchQueue.main.async {
                    self.errorMessage = error.localizedDescription
                    self.isLoading = false
                }
            }
        }
    }

    private func parseEquilibrium(_ raw: [String: Any]) -> EquilibriumOutput {
        let phases = raw["phases"] as? [String] ?? []
        let fractions = raw["fractions"] as? [Double] ?? []
        let comps = raw["compositions"] as? [String: [String: Double]] ?? [:]
        let elementsArr = raw["elements"] as? [String] ?? []
        let gm = raw["gm"] as? Double
        return EquilibriumOutput(phases: phases, fractions: fractions,
                                 compositions: comps, elements: elementsArr, gm: gm)
    }
}
