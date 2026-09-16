import SwiftUI
import AppKit

struct PourbaixView: View {
    @EnvironmentObject var model: AppModel
    @State private var image: NSImage?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                    Text("Diagram Pourbaix (E-pH) - Fe/H2O")
                        .font(.title.bold())
                    Text("Diagram stabilitas elektrokimia besi pada 25 °C: garis air (O2/H2O, H2O/H2), garis keseimbangan Fe/Fe2+/Fe3+, serta batas fasa padat Fe3O4 dan Fe2O3. Untuk studi korosi.")
                        .font(.caption).foregroundColor(.secondary)
                    Button("Gambar Diagram Pourbaix") { doRender() }.buttonStyle(.borderedProminent)
                    PlotResultView(
                        title: "Diagram Pourbaix - Fe/H2O",
                        subtitle: "298 K",
                        hint: "Tekan Gambar Diagram Pourbaix.",
                        image: image, isLoading: isLoading, errorMessage: errorMessage)
            }.padding(20)
        }
        .onAppear { doRender() }
    }

    func doRender() {
        image = nil
        errorMessage = nil
        isLoading = true
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("thermoapp_pb_\(UUID().uuidString).png")
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                let file = try model.bridge.pourbaix(outPath: dir.path)
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
