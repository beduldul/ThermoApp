import SwiftUI

/// Modul Reaksi — ΔG, ΔH, ΔS untuk reaksi stoikiometri.
struct ReactionView: View {
    @EnvironmentObject var model: AppModel

    // Reaktan & produk sebagai pasangan (koefisien, spesies)
    @State private var reactants: [(Double, String)] = [(1.0, "FeO(s)"), (1.0, "C(s,grafit)")]
    @State private var products: [(Double, String)] = [(1.0, "Fe(s)"), (1.0, "CO(g)")]
    @State private var temperature: Double = 1200.0
    @State private var result: ReactionOutput?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Termodinamika Reaksi")
                    .font(.title.bold())
                Text("ΔG, ΔH, ΔS untuk reaksi stoikiometri, dengan data termokimia standar (ΔHf, S298, Cp) dan koreksi Kirchhoff.")
                    .font(.caption).foregroundColor(.secondary)

                HStack(alignment: .top, spacing: 24) {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Reaktan")
                            .font(.headline)
                        ForEach(reactants.indices, id: \.self) { i in
                            speciesRow(coef: $reactants[i].0, species: $reactants[i].1,
                                       speciesList: REACTION_SPECIES,
                                       onRemove: { reactants.remove(at: i) })
                        }
                        Button("+ Tambah reaktan") { reactants.append((1.0, REACTION_SPECIES[0])) }

                        Text("Produk")
                            .font(.headline)
                        ForEach(products.indices, id: \.self) { i in
                            speciesRow(coef: $products[i].0, species: $products[i].1,
                                       speciesList: REACTION_SPECIES,
                                       onRemove: { products.remove(at: i) })
                        }
                        Button("+ Tambah produk") { products.append((1.0, REACTION_SPECIES[0])) }

                        HStack {
                            Text("Suhu (K)")
                            TextField("T", value: $temperature, format: .number)
                                .textFieldStyle(.roundedBorder).frame(width: 110)
                        }

                        Button(action: runReaction) {
                            if isLoading { ProgressView() } else { Text("Hitung Reaksi") }
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(isLoading)
                    }
                    .frame(maxWidth: 380, alignment: .leading)

                    // Hasil
                    VStack(alignment: .leading, spacing: 12) {
                        if let err = errorMessage {
                            HStack(spacing: 8) {
                                Image(systemName: "exclamationmark.triangle.fill").foregroundColor(.red)
                                Text(err).font(.callout)
                            }
                            .padding(10).background(Color.red.opacity(0.1))
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                        } else if let res = result {
                            metricGrid(res)
                            Text(res.note)
                                .font(.callout)
                                .padding(10)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(res.feasible ? Color.green.opacity(0.15) : Color.orange.opacity(0.15))
                                .clipShape(RoundedRectangle(cornerRadius: 8))
                        } else {
                            Text("Hasil akan tampil di sini.")
                                .font(.headline)
                            Text(
                                "Contoh: FeO(s) + C(s,grafit) -> Fe(s) + CO(g).\n"
                                + "Reaksi reduksi ini spontan pada suhu tinggi (ΔG < 0)."
                            )
                            .font(.caption).foregroundColor(.secondary)
                            .padding().background(Color(nsColor: .controlBackgroundColor))
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .padding(20)
        }
    }

    private func speciesRow(coef: Binding<Double>, species: Binding<String>,
                            speciesList: [String], onRemove: @escaping () -> Void) -> some View {
        HStack {
            TextField("koef", value: coef, format: .number.precision(.fractionLength(2)))
                .textFieldStyle(.roundedBorder).frame(width: 64)
            Picker("", selection: species) {
                ForEach(speciesList, id: \.self) { Text($0) }
            }
            .labelsHidden()
            Button(action: onRemove) { Image(systemName: "minus.circle").foregroundColor(.red) }
                .buttonStyle(.plain)
        }
    }

    private func metricGrid(_ res: ReactionOutput) -> some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())],
                  spacing: 12) {
            metric("ΔG (kJ/mol)", res.dg / 1000, format: "%,.2f")
            metric("ΔH (kJ/mol)", res.dh / 1000, format: "%,.2f")
            metric("ΔS (J/mol·K)", res.ds, format: "%,.2f")
            metric("Status", res.feasible ? 1 : 0, format: "%.0f", labelValue: res.feasible ? "Spontan" : "Tidak spontan")
        }
    }

    private func metric(_ title: String, _ value: Double, format: String, labelValue: String? = nil) -> some View {
        VStack {
            Text(title).font(.caption).foregroundColor(.secondary)
            if let lv = labelValue {
                Text(lv).font(.title3.bold())
            } else {
                Text(String(format: format, value)).font(.title3.bold())
            }
        }
        .padding(10).frame(maxWidth: .infinity)
        .background(Color(nsColor: .controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private func runReaction() {
        isLoading = true
        errorMessage = nil
        let r = reactants.map { "\($0.0):\($0.1)" }
        let p = products.map { "\($0.0):\($0.1)" }
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                let raw = try model.bridge.reaction(reactants: r, products: p, T: temperature)
                let out = ReactionOutput(
                    dg: raw["dg"] as? Double ?? 0,
                    dh: raw["dh"] as? Double ?? 0,
                    ds: raw["ds"] as? Double ?? 0,
                    feasible: raw["feasible"] as? Bool ?? false,
                    note: raw["note"] as? String ?? "")
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
}
