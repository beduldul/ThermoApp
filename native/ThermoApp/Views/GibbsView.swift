import SwiftUI
import AppKit

struct GibbsView: View {
    @EnvironmentObject var model: AppModel
    let CATS = ["Oksida", "Karbida", "Nitrida", "Sulfida", "Klorida"]
    @State private var selected = Set<String>(["Oksida", "Sulfida"])
    @State private var tmin = 300.0
    @State private var tmax = 1800.0
    @State private var image: NSImage?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Energi Gibbs vs Temperatur (stabilitas senyawa)")
                    .font(.title.bold())
                Text("ΔG pembentukan dari unsur untuk berbagai senyawa (oksida, karbida, nitrida, sulfida, klorida). Semakin negatif, semakin stabil.")
                    .font(.caption).foregroundColor(.secondary)

                Text("Kategori senyawa").font(.headline)
                HStack(spacing: 16) {
                    ForEach(CATS, id: \.self) { cat in
                        Toggle(cat, isOn: Binding(
                            get: { selected.contains(cat) },
                            set: { on in
                                if on { selected.insert(cat) } else { selected.remove(cat) }
                            }))
                    }
                }
                HStack {
                    Text("T min (K)"); TextField("", value: $tmin, format: .number).textFieldStyle(.roundedBorder).frame(width: 90)
                    Text("T max (K)"); TextField("", value: $tmax, format: .number).textFieldStyle(.roundedBorder).frame(width: 90)
                    Button("Gambar Diagram") { doRender() }.buttonStyle(.borderedProminent)
                }
                PlotResultView(
                    title: "Gibbs vs Temperatur",
                    subtitle: "Kategori: \(Array(selected).sorted().joined(separator: ", "))",
                    hint: "Pilih kategori, lalu tekan Gambar Plot.",
                    image: image, isLoading: isLoading, errorMessage: errorMessage)
            }.padding(20)
        }
        .onAppear { doRender() }
    }

    func doRender() {
        let cats = Array(selected).sorted()
        guard !cats.isEmpty else {
            errorMessage = "Pilih minimal satu kategori."
            return
        }
        image = nil
        errorMessage = nil
        isLoading = true
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("thermoapp_gib_\(UUID().uuidString).png")
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                let file = try model.bridge.gibbs(categories: cats, tmin: tmin, tmax: tmax, outPath: dir.path)
                if let img = NSImage(contentsOfFile: file) {
                    DispatchQueue.main.async {
                        self.image = img
                        self.isLoading = false
                    }
                } else {
                    throw EngineError.badOutput("Gagal memuat gambar: \(file)")
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
