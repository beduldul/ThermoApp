import SwiftUI
import AppKit

struct EllinghamView: View {
    @EnvironmentObject var model: AppModel

    @State private var oxids = [
        "4/3Fe -> 2/3Fe₂O₃","3/2Fe -> 1/2Fe₃O₄","2Fe -> 2FeO",
        "4/3Al -> 2/3Al₂O₃","Si -> SiO₂","Ti -> TiO₂","2Mg -> 2MgO",
        "2Ca -> 2CaO","2Mn -> 2MnO","4/3Cr -> 2/3Cr₂O₃","4/3V -> 2/3V₂O₃",
        "Mo -> MoO₃","W -> WO₃","2Co -> 2CoO","2Ni -> 2NiO",
        "Sn -> SnO₂","2Pb -> 2PbO","2Zn -> 2ZnO","4Cu -> 2Cu₂O",
    ]
    @State private var reds = ["C -> CO₂", "2C -> 2CO", "2H₂ -> 2H₂O"]
    @State private var selected = Set<String>()
    @State private var selectedReds = Set<String>(["C -> CO₂", "2C -> 2CO"])
    @State private var tmin = 400.0
    @State private var tmax = 1800.0
    @State private var image: NSImage?
    @State private var isLoading = false
    @State private var errorMessage: String?

    init() {
        _selected = State(initialValue: ["2Fe -> 2FeO", "4/3Al -> 2/3Al₂O₃", "Si -> SiO₂"])
    }

    /// Ambil label terkini dari engine (jauh lebih tangguh terhadap perubahan
    /// database); bila gagal, pakai daftar bawaan yang sudah selaras.
    private func loadLabels() {
        DispatchQueue.global(qos: .userInitiated).async {
            let fallbackOx = self.oxids
            let fallbackRd = self.reds
            let result: (ox: [String], rd: [String])
            if let lab = try? self.model.bridge.labels() {
                result = (lab.oxidation, lab.reductants)
            } else {
                result = (fallbackOx, fallbackRd)
            }
            DispatchQueue.main.async {
                if !result.ox.isEmpty { self.oxids = result.ox }
                if !result.rd.isEmpty { self.reds = result.rd }
                // pastikan default yang dipilih tetap valid
                let valid = Set(self.oxids)
                self.selected = self.selected.intersection(valid)
                if self.selected.isEmpty, let first = self.oxids.first {
                    self.selected = [first]
                }
            }
        }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Ellingham Diagram (ΔG vs T)")
                    .font(.title.bold())
                Text("Stabilitas oksida per mol O₂. Garis reduktor karbon (2C -> 2CO) menurun terhadap suhu; logam dapat mereduksi oksida bila garis karbon berada di bawah garis oksida.")
                    .font(.caption).foregroundColor(.secondary)

                Text("Pilih oksida").font(.headline)
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 240))], spacing: 6) {
                    ForEach(oxids, id: \.self) { o in
                        Toggle(o, isOn: Binding(
                            get: { selected.contains(o) },
                            set: { on in
                                if on { selected.insert(o) } else { selected.remove(o) }
                            }))
                    }
                }
                Text("Reduktor").font(.headline)
                HStack(spacing: 16) {
                    ForEach(reds, id: \.self) { r in
                        Toggle(r, isOn: Binding(
                            get: { selectedReds.contains(r) },
                            set: { on in
                                if on { selectedReds.insert(r) } else { selectedReds.remove(r) }
                            }))
                    }
                }
                HStack {
                    Text("T min (K)"); TextField("", value: $tmin, format: .number).textFieldStyle(.roundedBorder).frame(width: 90)
                    Text("T max (K)"); TextField("", value: $tmax, format: .number).textFieldStyle(.roundedBorder).frame(width: 90)
                    Button("Gambar Diagram") { doRender() }.buttonStyle(.borderedProminent)
                }

                PlotResultView(
                    title: "Ellingham Diagram",
                    subtitle: "Reaksi: \(Array(selected).sorted().count) oksida + \(Array(selectedReds).sorted().count) reduktor",
                    hint: "Pilih oksida & reduktor, lalu tekan Gambar Diagram.",
                    image: image, isLoading: isLoading, errorMessage: errorMessage)
            }.padding(20)
        }
        .onAppear { loadLabels() }
    }

    func doRender() {
        let ox = Array(selected).sorted()
        let rd = Array(selectedReds).sorted()
        guard !ox.isEmpty else {
            errorMessage = "Pilih minimal satu oksida."
            return
        }
        image = nil
        errorMessage = nil
        isLoading = true
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("thermoapp_el_\(UUID().uuidString).png")
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                let f = try model.bridge.ellingham(
                    oxids: ox, reductants: rd, tmin: tmin, tmax: tmax, outPath: dir.path)
                if let img = NSImage(contentsOfFile: f) {
                    DispatchQueue.main.async {
                        self.image = img
                        self.isLoading = false
                    }
                } else {
                    throw EngineError.badOutput("Gagal memuat gambar: \(f)")
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
