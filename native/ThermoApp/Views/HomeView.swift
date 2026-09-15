import SwiftUI
import AppKit

/// Beranda — ringkasan aplikasi.
struct HomeView: View {
    /// Logo yang disalin ke Resources saat build (lihat build.sh).
    private var logoImage: NSImage? {
        if let p = Bundle.main.path(forResource: "logo_hd", ofType: "png") {
            return NSImage(contentsOfFile: p)
        }
        return NSImage(systemSymbolName: "flame.fill", accessibilityDescription: nil)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                HStack(spacing: 20) {
                    if let img = logoImage {
                        Image(nsImage: img)
                            .resizable()
                            .scaledToFit()
                            .frame(width: 96, height: 96)
                            .shadow(radius: 3)
                    }
                    VStack(alignment: .leading, spacing: 4) {
                        Text("ThermoApp")
                            .font(.largeTitle.bold())
                        Text("Perhitungan termodinamika untuk praktikum Metalurgi")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                }

                Text(
                    "Aplikasi gratis dan berjalan asli di macOS. Menggunakan CALPHAD "
                    + "(`pycalphad`) untuk menghitung kesetimbangan fasa, reaksi, dan "
                    + "diagram yang umum dipakai di mata kuliah metalurgi dan material."
                )
                .padding()

                Divider()

                Text("Modul")
                    .font(.title2.bold())
                VStack(alignment: .leading, spacing: 10) {
                    moduleRow(icon: "scalemass.fill", name: "Equilib",
                              desc: "Kesetimbangan fasa — minimasi energi Gibbs")
                    moduleRow(icon: "testtube.2", name: "Reaksi",
                              desc: "ΔG, ΔH, ΔS untuk reaksi stoikiometri")
                    moduleRow(icon: "chart.xyaxis.line", name: "Diagram Fasa Biner",
                              desc: "Kurva likuidus/solidus dari database CALPHAD")
                    moduleRow(icon: "arrow.down.right.circle", name: "Ellingham",
                              desc: "ΔG vs T oksidasi logam dan reduktor (C, CO, H₂)")
                    moduleRow(icon: "clock.fill", name: "TTT",
                              desc: "Diagram transformasi baja karbon (Kirkaldy)")
                    moduleRow(icon: "chart.line.uptrend.xyaxis", name: "Gibbs-T",
                              desc: "Kestabilan senyawa oksida, karbida, nitrida, sulfida")
                    moduleRow(icon: "drop.fill", name: "Pourbaix",
                              desc: "Diagram E–pH sistem Fe–H₂O (korosi)")
                }

                Divider()

                Text("Satuan")
                    .font(.title2.bold())
                Text("Suhu dalam Kelvin (K) · Energi dalam Joule (J) · Tekanan dalam pascal (Pa).")
                    .padding()
            }
            .padding(24)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private func moduleRow(icon: String, name: String, desc: String) -> some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .frame(width: 28)
                .foregroundColor(.blue)
            VStack(alignment: .leading) {
                Text(name).font(.headline)
                Text(desc).font(.subheadline).foregroundColor(.secondary)
            }
        }
    }
}
