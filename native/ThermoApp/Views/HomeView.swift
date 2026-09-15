import SwiftUI

/// Beranda — ringkasan aplikasi.
struct HomeView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                HStack(spacing: 12) {
                    Image(systemName: "flame.fill")
                        .font(.system(size: 40))
                        .foregroundColor(.orange)
                    VStack(alignment: .leading) {
                        Text("ThermoApp")
                            .font(.largeTitle.bold())
                        Text("Perhitungan termodinamika untuk praktikum Metalurgi")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                }

                Text(
                    "Aplikasi open-source, gratis, dan berjalan asli di macOS. "
                    + "Dibangun di atas mesin CALPHAD (`pycalphad`) — pustaka yang "
                    + "dipakai luas dalam riset dan pendidikan termodinamika material. "
                    + "Bukan tiruan dari software komersial berlisensi."
                )
                .padding()

                Divider()

                Text("Modul")
                    .font(.title2.bold())
                VStack(alignment: .leading, spacing: 8) {
                    moduleRow(icon: "scalemass.fill", name: "Equilib",
                              desc: "Kesetimbangan fasa — minimasi energi Gibbs")
                    moduleRow(icon: "testtube.2", name: "Reaksi",
                              desc: "ΔG, ΔH, ΔS untuk reaksi stoikiometri")
                    moduleRow(icon: "chart.xyaxis.line", name: "Diagram Fasa Biner",
                              desc: "Kurva likuidus/solidus T–X dari database CALPHAD")
                }

                Divider()

                Text("Satuan")
                    .font(.title2.bold())
                Text("Suhu dalam Kelvin (K) · Energi dalam Joule (J) · Tekanan dalam pascal (Pa).")
                    .padding()

                Spacer()
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
