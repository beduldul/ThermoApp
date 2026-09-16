import SwiftUI
import AppKit

/// Komponen tampilan hasil plot yang STATELESS.
/// Semua status (gambar, loading, error) dimiliki oleh parent view via @State
/// dan dilewatkan ke sini. Dengan begitu mutasi dari DispatchQueue.main.async
/// selalu memicu re-render — pola yang sama seperti Equilib/PhaseDiagram.
struct PlotResultView: View {
    let title: String
    let subtitle: String
    let hint: String
    let image: NSImage?
    let isLoading: Bool
    let errorMessage: String?

    init(title: String,
         subtitle: String,
         hint: String,
         image: NSImage? = nil,
         isLoading: Bool = false,
         errorMessage: String? = nil) {
        self.title = title
        self.subtitle = subtitle
        self.hint = hint
        self.image = image
        self.isLoading = isLoading
        self.errorMessage = errorMessage
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(title).font(.title.bold())
            Text(subtitle).font(.caption).foregroundColor(.secondary)
            if isLoading {
                ProgressView("Menghitung...").frame(maxWidth: .infinity, maxHeight: 200)
            } else if let err = errorMessage {
                HStack(spacing: 8) {
                    Image(systemName: "exclamationmark.triangle.fill").foregroundColor(.red)
                    Text(err).font(.callout)
                }.padding(10).background(Color.red.opacity(0.1))
                .clipShape(RoundedRectangle(cornerRadius: 8))
            } else if let img = image {
                Image(nsImage: img).resizable().interpolation(.high).scaledToFit()
                    .frame(maxWidth: 960).background(Color.white)
                    .clipShape(RoundedRectangle(cornerRadius: 8)).shadow(radius: 2)
            } else {
                Text(hint).font(.headline).padding()
                    .frame(maxWidth: .infinity, maxHeight: 260, alignment: .center)
                    .background(Color(nsColor: .controlBackgroundColor))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
        }.padding(20)
    }
}
