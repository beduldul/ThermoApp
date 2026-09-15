import SwiftUI

@main
struct ThermoAppApp: App {
    @StateObject private var model = AppModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(model)
                .frame(minWidth: 760, minHeight: 560)
        }
        .windowStyle(.automatic)
    }
}
