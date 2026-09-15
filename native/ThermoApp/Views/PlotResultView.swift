import SwiftUI
import AppKit

var _lastPlotURL: URL?
func lastPlotURL() -> URL? { _lastPlotURL }
func setLastPlotURL(_ u: URL) { _lastPlotURL = u }

struct PlotResultView: View {
    let title: String
    let subtitle: String
    let hint: String
    let action: () -> (Bool, String?)
    @State private var image: NSImage?
    @State private var isLoading = false
    @State private var errorMessage: String?
    @EnvironmentObject var model: AppModel

    var body: some View {
        ScrollView {
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

    func render() {
        isLoading = true
        errorMessage = nil
        image = nil
        DispatchQueue.global(qos: .userInitiated).async {
            let (ok, err) = action()
            DispatchQueue.main.async {
                if ok, let url = lastPlotURL() {
                    self.image = NSImage(contentsOf: url)
                } else if !ok {
                    self.errorMessage = err
                }
                self.isLoading = false
            }
        }
    }
}
