import SwiftUI
import AppKit

struct TTTView: View {
    @EnvironmentObject var model: AppModel
    @State private var c = 0.8
    @State private var mn = 0.5
    @State private var cr = 0.0
    @State private var mo = 0.0
    @State private var result = PlotResultView(
        title: "", subtitle: "", hint: "", action: { (false, nil) })

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("Diagram TTT (Time-Temperature-Transformation)")
                    .font(.title.bold())
                Text("Kurva transformasi austenit untuk baja karbon (model Kirkaldy pend. pendidikan). Sumbu-x log waktu. Menunjukkan nose, kurva start (1%) & finish (99%), serta garis Ms/Mf.")
                    .font(.caption).foregroundColor(.secondary)

                VStack(alignment: .leading, spacing: 8) {
                    Label("Komposisi baja (wt%)", systemImage: "flask.fill").font(.headline)
                    HStack {
                        row("C", $c); row("Mn", $mn); row("Cr", $cr); row("Mo", $mo)
                    }
                    Button("Gambar Diagram TTT") { doRender() }.buttonStyle(.borderedProminent)
                }

                result
            }.padding(20)
        }
    }

    func row(_ name: String, _ v: Binding<Double>) -> some View {
        HStack {
            Text(name)
            TextField("", value: v, format: .number.precision(.fractionLength(1)))
                .textFieldStyle(.roundedBorder).frame(width: 70)
        }
    }

    func makeView() -> PlotResultView {
        PlotResultView(
            title: "Diagram TTT",
            subtitle: String(format: "Baja C %.2f%% Mn %.1f%% Cr %.1f%% Mo %.1f%%", c, mn, cr, mo),
            hint: "Atur komposisi, lalu tekan Gambar Diagram TTT.",
            action: {
                let dir = FileManager.default.temporaryDirectory
                    .appendingPathComponent("thermoapp_ttt_\(UUID().uuidString).png")
                setLastPlotURL(dir)
                do {
                    let _ = try model.bridge.ttt(c: c, mn: mn, cr: cr, mo: mo, si: 0.1, outPath: dir.path)
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
