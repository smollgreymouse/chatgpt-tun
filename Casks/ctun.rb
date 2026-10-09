cask "ctun" do
  version "0.3.1"
  sha256 :no_check

  url "https://github.com/smollgreymouse/ctun/releases/download/v#{version}/ctun_#{version}_macos_arm64.pkg"
  name "CTUN"
  desc "Detached multi-project MCP gateway for ChatGPT"
  homepage "https://github.com/smollgreymouse/ctun"

  depends_on arch: :arm64
  depends_on formula: "python@3.12"
  depends_on cask: "ngrok"

  pkg "ctun_#{version}_macos_arm64.pkg"

  uninstall pkgutil: "dev.smollgreymouse.ctun"

  caveats <<~EOS
    Authenticate ngrok once: ngrok config add-authtoken YOUR_TOKEN
    Then initialize CTUN: ctun setup
    Existing ~/.local/state/ctun configuration is preserved.
  EOS
end
