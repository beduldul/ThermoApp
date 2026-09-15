import SwiftUI
import AppKit

struct EllinghamView: View {
    @EnvironmentObject var model: AppModel

    let OXIDS = [
        "4/3Fe -> 2/3Fe2O3","3/2Fe -> 1/2Fe3O4","2Fe -> 2FeO",
        "4/3Al -> 2/3Al2O3","Si -> SiO2","Ti -> TiO2","2Mg -> 2MgO",
        "2Ca -> 2CaO","2Mn -> 2MnO","4/3Cr -> 2/3Cr2O3","4/3V -> 2/3V2O3",
        "Mo -> MoO3","W -> WO3","2Co -> 2CoO","2Ni -> 2NiO",
        "Sn -> SnO2","2Pb -> 2PbO","2Zn -> 2ZnO","4Cu -> 2Cu2O",
    ]
    let REDS = ["C -> CO2", "2C -> 2CO", "2H2 -> 2H2O"]

    @State private var selected = Set<String>()
    @State private var selectedReds = Set<String>(["C -> CO2", "2C -> 2CO"])
    @State private var tmin = 400.0
    @State private var tmax = 1800.0
    @State private var result = PlotResultView(
        title: "", subtitle: "", hint: "", action: { (false, nil) })

    init() {
        _selected = State(initialValue: ["2Fe -> 2FeO", "4/3Al -> 2/3Al2O3", "Si -> SiO2"])
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Ellingham Diagram (dG vs T)")
                    .font(.title.bold())
                Text("Stabilitas oksida per mol O2. Garis reduktor karbon (2C->2CO) menurun dengan T; logam dapat mereduksi oksida bila garis C berada di bawah garis oksida.")
                    .font(.caption).foregroundColor(.secondary)

                Text("Pilih oksida").font(.headline)
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 240))], spacing: 6) {
                    ForEach(OXIDS, id: \.self) { o in
                        Toggle(o, isOn: Binding(
                            get: { selected.contains(o) },
                            set: { on in
                                if on { selected.insert(o) } else { selected.remove(o) }
                            }))
                    }
                }
                Text("Reduktor").font(.headline)
                HStack(spacing: 16) {
                    ForEach(REDS, id: \.self) { r in
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

                result
                    .onAppear {
                        result = makeView()
                    }
            }.padding(20)
        }
    }

    func makeView() -> PlotResultView {
        let ox = Array(selected).sorted()
        let rd = Array(selectedReds).sorted()
        return PlotResultView(
            title: "Ellingham Diagram",
            subtitle: "Reaksi: \(ox.count) oksida + \(rd.count) reduktor",
            hint: "Pilih oksida & reduktor, lalu tekan Gambar Diagram.",
            action: {
                let dir = FileManager.default.temporaryDirectory
                    .appendingPathComponent("thermoapp_el_\(UUID().uuidString).png")
                setLastPlotURL(dir)
                do {
                    let f = try model.bridge.ellingham(
                        oxids: ox, reductants: rd, tmin: tmin, tmax: tmax, outPath: dir.path)
                    return (true, nil)
                } catch {
                    return (false, error.localizedDescription)
                }
            })
    }

    func doRender() {
        result = makeView()
        // render setelah view ter-pasang
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { result.render() }
    }
}
