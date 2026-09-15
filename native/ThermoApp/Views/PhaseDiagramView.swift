import SwiftUI
import AppKit

/// Modul Diagram Fasa Biner — menampilkan PNG hasil engine.
struct PhaseDiagramView: View {
    @EnvironmentObject var model: AppModel

    @State private var dbID: String = ""
    @State private var elements: [String] = []
    @State private var compA: String = ""
    @State private var compB: String = ""
    @State private var tmin: Double = 300.0
    @State private var tmax: Double = 2000.0
    @State private var nx: Int = 50
    @State private var image: NSImage?
    @State private var isLoading = false
    @State private var errorMessage: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("📈 Diagram Fasa Biner (T–X)")
                    .font(.title.bold())
                Text("Kurva likuidus/solidus dan garis invarian dari database CALPHAD, dihitung dengan algoritme ZPF boundary.")
                    .font(.caption).foregroundColor(.secondary)

                // Kontrol
                HStack(alignment: .top, spacing: 20) {
                    VStack(alignment: .leading, spacing: 10) {
                        Picker("Database", selection: $dbID) {
                            ForEach(model.databases) { db in
                                Text("\(db.label) — \(db.elements)").tag(db.id)
                            }
                        }
                        .onChange(of: dbID) { _, new in loadElements(for: new) }

                        HStack {
                            Picker("Elemen A", selection: $compA) {
                                ForEach(elements, id: \.self) { Text($0) }
                            }
                            Picker("Elemen B", selection: $compB) {
                                ForEach(elements, id: \.self) { Text($0) }
                            }
                        }

                        HStack {
                            Text("T min (K)")
                            TextField("", value: $tmin, format: .number)
                                .textFieldStyle(.roundedBorder).frame(width: 90)
                            Text("T max (K)")
                            TextField("", value: $tmax, format: .number)
                                .textFieldStyle(.roundedBorder).frame(width: 90)
                        }
                        HStack {
                            Text("Resolusi: ")
                            Slider(value: Binding(get: { Double(nx) }, set: { nx = Int($0) }),
                                   in: 30...100, step: 10)
                        }

                        Button(action: runPhaseDiagram) {
                            if isLoading { ProgressView() } else { Text("Gambar Diagram Fasa") }
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(isLoading || dbID.isEmpty || compA.isEmpty || compB.isEmpty)
                    }
                    .frame(maxWidth: 360, alignment: .leading)
                }

                // Hasil gambar
                if let err = errorMessage {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill").foregroundColor(.red)
                        Text(err).font(.callout)
                    }
                    .padding(10).background(Color.red.opacity(0.1))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                } else if let img = image {
                    Image(nsImage: img)
                        .resizable()
                        .interpolation(.high)
                        .scaledToFit()
                        .frame(maxWidth: 900)
                        .background(Color.white)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                        .shadow(radius: 2)
                } else {
                    Text("Pilih database dan elemen, lalu tekan **Gambar Diagram Fasa**.")
                        .font(.headline).padding()
                        .frame(maxWidth: .infinity, maxHeight: 300, alignment: .center)
                        .background(Color(nsColor: .controlBackgroundColor))
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }
            .padding(20)
        }
        .onAppear(perform: selectDefaultDB)
    }

    func selectDefaultDB() {
        guard dbID.isEmpty, !model.databases.isEmpty else { return }
        dbID = model.databases.first?.id ?? ""
        loadElements(for: dbID)
    }

    func loadElements(for id: String) {
        guard let db = model.databases.first(where: { $0.id == id }) else { return }
        let list = db.elements.split(separator: "-").map { String($0).trimmingCharacters(in: .whitespaces) }
        elements = list
        if !list.isEmpty {
            compA = list[0]
            compB = list.count > 1 ? list[1] : list[0]
        }
    }

    func runPhaseDiagram() {
        isLoading = true
        errorMessage = nil
        let tempDir = FileManager.default.temporaryDirectory
        let outPath = tempDir.appendingPathComponent("thermoapp_diagram_\(UUID().uuidString).png").path

        DispatchQueue.global(qos: .userInitiated).async {
            do {
                let file = try model.bridge.phaseDiagram(
                    db: dbID, A: compA, B: compB,
                    tmin: tmin, tmax: tmax, nx: nx, outPath: outPath)
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
