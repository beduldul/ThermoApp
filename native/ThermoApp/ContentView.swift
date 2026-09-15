import SwiftUI

/// Kontainer utama dengan navigasi berbasis tab.
struct ContentView: View {
    @State private var selection = 0

    var body: some View {
        TabView(selection: $selection) {
            HomeView()
                .tabItem { Label("Beranda", systemImage: "house.fill") }
                .tag(0)

            EquilibView()
                .tabItem { Label("Equilib", systemImage: "scalemass.fill") }
                .tag(1)

            ReactionView()
                .tabItem { Label("Reaksi", systemImage: "testtube.2") }
                .tag(2)

            PhaseDiagramView()
                .tabItem { Label("Diagram Fasa", systemImage: "chart.xyaxis.line") }
                .tag(3)
        }
        .navigationTitle("ThermoApp")
    }
}
