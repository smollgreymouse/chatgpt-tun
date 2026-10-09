cask "chatgpt-tun" do
  version "0.2.0"
  sha256 :no_check

  url "https://github.com/smollgreymouse/chatgpt-tun/releases/download/v#{version}/chatgpt-tun_#{version}_macos_arm64.pkg"
  name "CTUN"
  desc "Detached multi-project MCP gateway for ChatGPT"
  homepage "https://github.com/smollgreymouse/chatgpt-tun"

  depends_on arch: :arm64
  depends_on formula: "python@3.12"
  depends_on cask: "ngrok"

  pkg "chatgpt-tun_#{version}_macos_arm64.pkg"

  uninstall pkgutil: "dev.smollgreymouse.chatgpt-tun"

  caveats <<~EOS
    Authenticate ngrok once: ngrok config add-authtoken YOUR_TOKEN
    Then initialize CTUN: ctun setup
    Existing ~/.local/state/chatgpt-tun configuration is preserved.
  EOS
end
