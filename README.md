# 🔐 Crypto Seed Phrase Recovery Tool

A modern, open-source GUI tool to recover seed phrases for **Bitcoin, Ethereum, and Solana** when you forgot up to 5 words!

---

## ⬇️ Download

Get the latest version for your operating system:

| Operating System | Download |
|-------------------|----------|
| Windows (.exe)    | [Download Latest](https://github.com/0xpram/crypto-seed-recovery/releases/latest) |
| macOS (.app)      | [Download Latest](https://github.com/0xpram/crypto-seed-recovery/releases/latest) |
| Source Code       | [View on GitHub](https://github.com/0xpram/crypto-seed-recovery) |

---

## Features

- ✅ **Beautiful, modern dark-themed UI** (GitHub-style)
- ✅ **Multi-chain support**:
  - Bitcoin (BTC) – with multiple derivation paths and address types!
  - Ethereum (ETH)
  - Solana (SOL)
- ✅ **Supports 12, 18, or 24-word BIP39 seed phrases**
- ✅ **Supports 1 to 5 missing words**
- ✅ **Multiple Bitcoin derivation paths**:
  - Legacy (m/0'/0'/0/0)
  - BIP44 Legacy (m/44'/0'/0'/0/0)
  - BIP49 SegWit (m/49'/0'/0'/0/0)
  - BIP84 Native SegWit (m/84'/0'/0'/0/0) (default)
- ✅ **Multiple Bitcoin address types**:
  - Legacy (P2PKH)
  - SegWit (P2SH-P2WPKH)
  - Native SegWit (Bech32) (default)
- ✅ **Wallet address input for verification**
- ✅ Real-time progress bar with thousand separators
- ✅ Can be stopped at any time
- ✅ Complete console logging for debugging
- ✅ Save recovery results to a text file
- ✅ Fast and optimized

## Installation

### Option 1: Run from Source
1. **Clone or download this project**
2. **Install Python 3.7 or later** (https://www.python.org/downloads/)
3. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the app:**
   ```bash
   python seed_recovery.py
   ```

### Option 2: Build Executable
#### Windows
1. **Complete steps 1-3 from "Run from Source"**
2. **Run the build script:**
   ```bash
   build.bat
   ```
3. **Find the compiled .exe in the `dist` folder!**

#### macOS
1. **Complete steps 1-3 from "Run from Source"**
2. **Make build script executable:**
   ```bash
   chmod +x build.sh
   ```
3. **Run the build script:**
   ```bash
   ./build.sh
   ```
4. **Find the compiled executable in the `dist` folder!**

## Usage

1. **Select your chain** (BTC, ETH, or SOL) from the tabs
2. **Choose your seed phrase length** (12, 18, or 24 words)
3. **(For BTC only) Select derivation path and address type**
4. **Enter your partial seed phrase**: use `?` for missing words
5. **Enter the positions of the missing words** (comma-separated, e.g., `3,7` – note: positions start at 1)
6. **(Optional but recommended) Enter your wallet address to verify the correct seed**
7. Click **Start Recovery**

## Important Notes

- This tool recovers **BIP39 mnemonic seed phrases**, not individual private keys (WIF, etc.)
- The more missing words you have, the longer the recovery will take:
  - 1 missing word: ~2048 combinations (very fast!)
  - 2 missing words: ~4 million combinations
  - 3 missing words: ~8 billion combinations (very long!)
  - 4+ missing words: not feasible without specialized hardware
- Recovery speed depends on your computer's performance

## Safety & Security

- This tool runs locally on your computer – your seed phrase is never sent over the internet
- Always test with a demo seed first
- Consider running this tool on an air-gapped computer for maximum security

## Donation

If this tool helped you recover your funds, please consider donating to support future development! 🙏

**Bitcoin Address (Native SegWit):** `bc1qlde6za49es7m60mxf5trfnl57r6u8fjv3sccsa`

## License

MIT License

