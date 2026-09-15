import SwiftUI
import AppKit

struct PourbaixView: View {
    @EnvironmentObject var model: AppModel
    @State private var result = PlotResultView(
        title: "", subtitle: "", hint: "", action: { (false, nil) })

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                    Text("Diagram Pourbaix (E-pH) - Fe/H2O")
                        .font(.title.bold())
                    Text("Diagram stabilitas elektrokimia besi pada 25 °C: garis air (O2/H2O, H2O/H2), garis keseimbangan Fe/Fe2+/Fe3+, serta batas fasa padat Fe3O4 dan Fe2O3. Untuk studi korosi.")
                        .font(.caption).foregroundColor(.secondary)
                    Button("Gambar Diagram Pourbaix") { doRender() }.buttonStyle(.borderedProminent)
                    result
            }.padding(20)
        }
        .onAppear { doRender() }
    }

    func makeView() -> PlotResultView {
        PlotResultView(
            title: "Diagram Pourbaix - Fe/H2O",
            subtitle: "298 K",
            hint: "Tekan Gambar Diagram Pourbaix.",
            action: {
                let dir = FileManager.default.temporaryDirectory
                    .appendingPathComponent("thermoapp_pb_\(UUID().uuidString).png")
                setLastPlotURL(dir)
                do {
                    let _ = try model.bridge.pourbaix(outPath: dir.path)
                    return (true, nil)
                } catch {
                    return (false, error.localizedDescription)
                }
            })
    }

    func doRender() {
        result = makeView()
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { result.render() }
    }
}
