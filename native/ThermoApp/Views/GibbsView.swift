import SwiftUI
import AppKit

struct GibbsView: View {
    @EnvironmentObject var model: AppModel
    let CATS = ["Oksida", "Karbida", "Nitrida", "Sulfida", "Klorida"]
    @State private var selected = Set<String>(["Oksida", "Sulfida"])
    @State private var tmin = 300.0
    @State private var tmax = 1800.0
    @State private var result = PlotResultView(
        title: "", subtitle: "", hint: "", action: { (false, nil) })

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Energi Gibbs vs Temperatur (stabilitas senyawa)")
                    .font(.title.bold())
                Text("dG pembentukan dari unsur untuk berbagai senyawa (oksida, karbida, nitrida, sulfida, klorida). Semakin negatif, semakin stabil.")
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
                    Button("Gambar Plot") { doRender() }.buttonStyle(.borderedProminent)
                }
                result
            }.padding(20)
        }
    }

    func makeView() -> PlotResultView {
        let cats = Array(selected).sorted()
        return PlotResultView(
            title: "Gibbs vs Temperatur",
            subtitle: "Kategori: \(cats.joined(separator: ", "))",
            hint: "Pilih kategori, lalu tekan Gambar Plot.",
            action: {
                let dir = FileManager.default.temporaryDirectory
                    .appendingPathComponent("thermoapp_gib_\(UUID().uuidString).png")
                setLastPlotURL(dir)
                do {
                    let _ = try model.bridge.gibbs(categories: cats, tmin: tmin, tmax: tmax, outPath: dir.path)
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
