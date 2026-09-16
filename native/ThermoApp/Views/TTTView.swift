import SwiftUI
import AppKit

struct TTTView: View {
    @EnvironmentObject var model: AppModel
    @State private var c = 0.8
    @State private var mn = 0.5
    @State private var cr = 0.0
    @State private var mo = 0.0
    @State private var image: NSImage?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Diagram TTT (Time-Temperature-Transformation)")
                    .font(.title.bold())
                Text("Kurva transformasi austenit untuk baja karbon (model pendidikan, fenomenologis). Sumbu-x log waktu. Menunjukkan nose, kurva start (1%) & finish (99%), serta garis Ms/Mf.")
                    .font(.caption).foregroundColor(.secondary)

                VStack(alignment: .leading, spacing: 8) {
                    Label("Komposisi baja (wt%)", systemImage: "flask.fill").font(.headline)
                    HStack {
                        row("C", $c); row("Mn", $mn); row("Cr", $cr); row("Mo", $mo)
                    }
                    Button("Gambar Diagram TTT") { doRender() }.buttonStyle(.borderedProminent)
                }

                PlotResultView(
                    title: "Diagram TTT",
                    subtitle: String(format: "Baja C %.2f%% Mn %.1f%% Cr %.1f%% Mo %.1f%%", c, mn, cr, mo),
                    hint: "Atur komposisi, lalu tekan Gambar Diagram TTT.",
                    image: image, isLoading: isLoading, errorMessage: errorMessage)
            }.padding(20)
        }
        .onAppear { doRender() }
    }

    func row(_ name: String, _ v: Binding<Double>) -> some View {
        HStack {
            Text(name)
            TextField("", value: v, format: .number.precision(.fractionLength(1)))
                .textFieldStyle(.roundedBorder).frame(width: 70)
        }
    }

    func doRender() {
        image = nil
        errorMessage = nil
        isLoading = true
        let dir = FileManager.default.temporaryDirectory
            .appendingPathComponent("thermoapp_ttt_\(UUID().uuidString).png")
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                let file = try model.bridge.ttt(c: c, mn: mn, cr: cr, mo: mo, si: 0.1, outPath: dir.path)
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
