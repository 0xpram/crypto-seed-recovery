import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
from mnemonic import Mnemonic
from datetime import datetime
import hashlib
import hmac
import struct
import base58
import coincurve
from eth_utils import keccak, to_checksum_address
from itertools import product
import bech32
from solders.keypair import Keypair
from solders.pubkey import Pubkey

# Modern theme colors
BG_DARK = "#0d1117"
BG_CARD = "#161b22"
BG_CONSOLE = "#010409"
ACCENT_BTC = "#f7931a"
ACCENT_ETH = "#627eea"
ACCENT_SOL = "#9945ff"
TEXT_PRIMARY = "#f0f6fc"
TEXT_SECONDARY = "#8b949e"
TEXT_SUCCESS = "#3fb950"

# Precompute word list as tuple for faster access
_mnemo = Mnemonic("english")
WORDLIST = tuple(_mnemo.wordlist)
WORD_SET = set(WORDLIST)

def hash160(data):
    return hashlib.new('ripemd160', hashlib.sha256(data).digest()).digest()

def sha256(data):
    return hashlib.sha256(data).digest()

def b58check_encode(data):
    checksum = sha256(sha256(data))[:4]
    return base58.b58encode(data + checksum).decode('ascii')

def derive_child_key(master_priv, master_chain, path):
    """Derive child private key using BIP32 path"""
    priv = master_priv
    chain = master_chain
    
    for index in path:
        if index & 0x80000000:
            # Hardened key
            data = b"\x00" + priv + struct.pack(">L", index)
        else:
            # Normal key
            pub = coincurve.PublicKey.from_secret(priv).format(compressed=True)
            data = pub + struct.pack(">L", index)
        I = hmac.new(chain, data, hashlib.sha512).digest()
        priv = I[:32]
        chain = I[32:]
    
    return priv

# Bitcoin path options
BTC_PATHS = {
    "Legacy (m/0'/0'/0/0)": [0x80000000, 0x80000000, 0, 0],
    "BIP44 Legacy (m/44'/0'/0'/0/0)": [0x80000000 | 44, 0x80000000, 0x80000000, 0, 0],
    "BIP49 SegWit (m/49'/0'/0'/0/0)": [0x80000000 | 49, 0x80000000, 0x80000000, 0, 0],
    "BIP84 Native SegWit (m/84'/0'/0'/0/0)": [0x80000000 | 84, 0x80000000, 0x80000000, 0, 0],
}

# Bitcoin address type options
BTC_ADDRESS_TYPES = {
    "Legacy (P2PKH)": "legacy",
    "SegWit (P2SH-P2WPKH)": "segwit",
    "Native SegWit (Bech32)": "bech32",
}

def derive_btc_address(seed_phrase, path_name="BIP84 Native SegWit (m/84'/0'/0'/0/0)", address_type="bech32"):
    seed_bytes = _mnemo.to_seed(seed_phrase)
    
    # Derive master key
    key = b"Bitcoin seed"
    I = hmac.new(key, seed_bytes, hashlib.sha512).digest()
    master_priv = I[:32]
    master_chain = I[32:]
    
    # Get path from options
    path = BTC_PATHS.get(path_name, BTC_PATHS["BIP84 Native SegWit (m/84'/0'/0'/0/0)"])
    priv_key = derive_child_key(master_priv, master_chain, path)
    
    # Generate compressed public key
    pub_key = coincurve.PublicKey.from_secret(priv_key).format(compressed=True)
    
    # Derive address based on type
    if address_type == "legacy":
        # Legacy (P2PKH)
        pub_key_hash = hash160(pub_key)
        address = b58check_encode(b"\x00" + pub_key_hash)
    elif address_type == "segwit":
        # SegWit (P2SH-P2WPKH)
        pub_key_hash = hash160(pub_key)
        redeem_script = b"\x00\x14" + pub_key_hash
        script_hash = hash160(redeem_script)
        address = b58check_encode(b"\x05" + script_hash)
    else:
        # Native SegWit (Bech32)
        pub_key_hash = hash160(pub_key)
        address = bech32.encode("bc", 0, pub_key_hash)
    
    return address

def derive_eth_address(seed_phrase):
    seed_bytes = _mnemo.to_seed(seed_phrase)
    
    # Derive m/44'/60'/0'/0/0 - standard Ethereum path
    key = b"Bitcoin seed"
    I = hmac.new(key, seed_bytes, hashlib.sha512).digest()
    master_priv = I[:32]
    master_chain = I[32:]
    
    path = [0x80000000 | 44, 0x80000000 | 60, 0x80000000, 0, 0]
    priv_key = derive_child_key(master_priv, master_chain, path)
    
    # Generate uncompressed public key
    pub_key = coincurve.PublicKey.from_secret(priv_key).format(compressed=False)
    # Ethereum address is last 20 bytes of keccak256 hash of pub key (without 0x04 prefix)
    pub_key_hash = keccak(pub_key[1:])
    address = to_checksum_address('0x' + pub_key_hash[-20:].hex())
    
    return address

def derive_solana_address(seed_phrase):
    seed_bytes = _mnemo.to_seed(seed_phrase)
    # Solana uses BIP44 m/44'/501'/0'/0' (hardened) and then first index 0
    key = b"Bitcoin seed"
    I = hmac.new(key, seed_bytes, hashlib.sha512).digest()
    master_priv = I[:32]
    master_chain = I[32:]
    
    path = [0x80000000 | 44, 0x80000000 | 501, 0x80000000, 0x80000000]
    priv_key = derive_child_key(master_priv, master_chain, path)
    
    # Create keypair from the derived private key
    keypair = Keypair.from_seed(priv_key)
    return str(keypair.pubkey())

class MultiChainSeedRecovery:
    def __init__(self, root):
        self.root = root
        self.root.title("🔐 Crypto Seed Phrase Recovery Tool (PRO)")
        self.root.geometry("1200x920")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(True, True)
        
        self.mnemo = _mnemo
        self.wordlist = WORDLIST
        self.is_running = False
        self.current_chain = "BTC"
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg=BG_DARK, pady=12)
        header.pack()
        
        title = tk.Label(header, text="🔐 Crypto Seed Phrase Recovery (PRO)", 
                        font=("Segoe UI", 22, "bold"), 
                        bg=BG_DARK, fg=TEXT_PRIMARY)
        title.pack()
        
        subtitle = tk.Label(header, text="Recover your seed phrase using partial words + wallet address (1-5 missing words)", 
                           font=("Segoe UI", 10), 
                           bg=BG_DARK, fg=TEXT_SECONDARY)
        subtitle.pack(pady=3)
        
        # Tabbed interface
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=8)
        
        # Create tabs
        self.tab_btc = tk.Frame(self.notebook, bg=BG_DARK)
        self.tab_eth = tk.Frame(self.notebook, bg=BG_DARK)
        self.tab_sol = tk.Frame(self.notebook, bg=BG_DARK)
        
        self.notebook.add(self.tab_btc, text=" Bitcoin ")
        self.notebook.add(self.tab_eth, text=" Ethereum ")
        self.notebook.add(self.tab_sol, text=" Solana ")
        
        # Setup each tab
        self.create_tab_content(self.tab_btc, ACCENT_BTC, "BTC")
        self.create_tab_content(self.tab_eth, ACCENT_ETH, "ETH")
        self.create_tab_content(self.tab_sol, ACCENT_SOL, "SOL")
        
        # Footer donation
        footer = tk.Frame(self.root, bg=BG_CARD, pady=15, padx=20)
        footer.pack(fill=tk.X)
        
        donate_title = tk.Label(footer, 
                              text="💝 If this tool helped you recover your funds, please consider donating to support development!",
                              font=("Segoe UI", 12, "bold"),
                              bg=BG_CARD,
                              fg=ACCENT_BTC)
        donate_title.pack(pady=(0, 8))
        
        # Donation address and copy button
        addr_frame = tk.Frame(footer, bg=BG_CARD)
        addr_frame.pack(pady=(0, 10))
        
        donate_address = tk.Label(addr_frame, 
                              text="bc1qlde6za49es7m60mxf5trfnl57r6u8fjv3sccsa",
                              font=("Consolas", 13),
                              bg=BG_DARK,
                              fg=TEXT_SUCCESS,
                              padx=12,
                              pady=6)
        donate_address.pack(side=tk.LEFT, padx=(0, 10))
        
        def copy_address():
            self.root.clipboard_clear()
            self.root.clipboard_append("bc1qlde6za49es7m60mxf5trfnl57r6u8fjv3sccsa")
            messagebox.showinfo("Copied!", "Donation address copied to clipboard!")
        
        copy_btn = tk.Button(addr_frame, 
                             text="📋 Copy Address",
                             font=("Segoe UI", 10, "bold"),
                             bg=TEXT_SUCCESS,
                             fg="black",
                             padx=15,
                             pady=6,
                             bd=0,
                             cursor="hand2",
                             relief=tk.FLAT,
                             activebackground=TEXT_SUCCESS,
                             activeforeground="black",
                             command=copy_address)
        copy_btn.pack(side=tk.LEFT)
        
    def create_tab_content(self, parent, accent, chain):
        # Main container
        main_container = tk.Frame(parent, bg=BG_DARK)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Top: Input Card
        input_card = tk.Frame(main_container, bg=BG_CARD, padx=20, pady=20)
        input_card.pack(fill=tk.X, pady=(0, 10))
        
        # Chain icon/title
        chain_header = tk.Frame(input_card, bg=BG_CARD)
        chain_header.pack(fill=tk.X, pady=(0, 15))
        
        icons = {"BTC": "₿", "ETH": "Ξ", "SOL": "◎"}
        chain_label = tk.Label(chain_header, 
                              text=f"{icons[chain]} {chain} Seed Recovery",
                              font=("Segoe UI", 17, "bold"),
                              bg=BG_CARD,
                              fg=accent)
        chain_label.pack(side=tk.LEFT)
        
        # Seed phrase length selector
        len_frame = tk.Frame(input_card, bg=BG_CARD)
        len_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(len_frame, text="Seed Phrase Length:", 
                font=("Segoe UI", 10), bg=BG_CARD, fg=TEXT_PRIMARY).pack(side=tk.LEFT, padx=(0,10))
        
        length_var = tk.StringVar(value="12")
        tk.Radiobutton(len_frame, text="12 words", variable=length_var, value="12", 
                      font=("Segoe UI", 10), bg=BG_CARD, fg=TEXT_PRIMARY, 
                      selectcolor=BG_DARK, activebackground=BG_CARD, activeforeground=TEXT_PRIMARY).pack(side=tk.LEFT, padx=6)
        tk.Radiobutton(len_frame, text="18 words", variable=length_var, value="18", 
                      font=("Segoe UI", 10), bg=BG_CARD, fg=TEXT_PRIMARY, 
                      selectcolor=BG_DARK, activebackground=BG_CARD, activeforeground=TEXT_PRIMARY).pack(side=tk.LEFT, padx=6)
        tk.Radiobutton(len_frame, text="24 words", variable=length_var, value="24", 
                      font=("Segoe UI", 10), bg=BG_CARD, fg=TEXT_PRIMARY, 
                      selectcolor=BG_DARK, activebackground=BG_CARD, activeforeground=TEXT_PRIMARY).pack(side=tk.LEFT, padx=6)
        
        # Bitcoin-specific options (path and address type)
        if chain == "BTC":
            btc_opts_frame = tk.Frame(input_card, bg=BG_CARD)
            btc_opts_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Path selector
            path_frame = tk.Frame(btc_opts_frame, bg=BG_CARD)
            path_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
            
            tk.Label(path_frame, text="Derivation Path:", 
                    font=("Segoe UI", 10), bg=BG_CARD, fg=TEXT_PRIMARY).pack(anchor=tk.W, pady=(0, 3))
            
            path_var = tk.StringVar(value="BIP84 Native SegWit (m/84'/0'/0'/0/0)")
            path_combo = ttk.Combobox(path_frame, textvariable=path_var, values=list(BTC_PATHS.keys()), state="readonly", font=("Consolas", 9))
            path_combo.pack(fill=tk.X)
            
            # Address type selector
            addr_type_frame = tk.Frame(btc_opts_frame, bg=BG_CARD)
            addr_type_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
            
            tk.Label(addr_type_frame, text="Address Type:", 
                    font=("Segoe UI", 10), bg=BG_CARD, fg=TEXT_PRIMARY).pack(anchor=tk.W, pady=(0, 3))
            
            addr_type_var = tk.StringVar(value="Native SegWit (Bech32)")
            addr_type_combo = ttk.Combobox(addr_type_frame, textvariable=addr_type_var, values=list(BTC_ADDRESS_TYPES.keys()), state="readonly", font=("Consolas", 9))
            addr_type_combo.pack(fill=tk.X)
            
            # Store the variables
            setattr(self, f"path_var_{chain}", path_var)
            setattr(self, f"addr_type_var_{chain}", addr_type_var)
        
        # Seed phrase input
        tk.Label(input_card, text="Seed Phrase (use '?' for missing words):", 
                font=("Segoe UI", 10), bg=BG_CARD, fg=TEXT_PRIMARY).pack(anchor=tk.W, pady=(6, 3))
        
        seed_text = scrolledtext.ScrolledText(input_card, 
                                             height=3, 
                                             font=("Consolas", 10),
                                             bg=BG_DARK, 
                                             fg=TEXT_PRIMARY, 
                                             insertbackground=accent,
                                             bd=0,
                                             relief=tk.FLAT)
        seed_text.pack(fill=tk.X, pady=(0, 10))
        seed_text.insert(tk.END, "dinosaur cram ? chase enter like ? answer boost bitter piano east")
        
        # Address and Positions row
        input_row = tk.Frame(input_card, bg=BG_CARD)
        input_row.pack(fill=tk.X, pady=(0, 10))
        
        # Wallet address
        addr_col = tk.Frame(input_row, bg=BG_CARD)
        addr_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(addr_col, text="Wallet Address (to verify):", 
                font=("Segoe UI", 10), bg=BG_CARD, fg=TEXT_PRIMARY).pack(anchor=tk.W, pady=(0, 3))
        
        addr_frame = tk.Frame(addr_col, bg=BG_DARK, padx=10, pady=8)
        addr_frame.pack(fill=tk.X)
        
        addr_entry = tk.Entry(addr_frame, 
                            font=("Consolas", 10), 
                            bg=BG_DARK, 
                            fg=TEXT_PRIMARY,
                            insertbackground=accent,
                            bd=0,
                            relief=tk.FLAT)
        addr_entry.pack(fill=tk.X)
        if chain == "BTC":
            addr_entry.insert(0, "1LdQg2TkvVty8LLbRVrD9feapQZBvWFyhp")
        
        # Positions of missing words
        pos_col = tk.Frame(input_row, bg=BG_CARD)
        pos_col.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        tk.Label(pos_col, text="Positions of missing words (e.g., 3,7):", 
                font=("Segoe UI", 10), bg=BG_CARD, fg=TEXT_PRIMARY).pack(anchor=tk.W, pady=(0, 3))
        
        pos_frame = tk.Frame(pos_col, bg=BG_DARK, padx=10, pady=8)
        pos_frame.pack(fill=tk.X)
        
        pos_entry = tk.Entry(pos_frame, 
                            font=("Consolas", 10), 
                            bg=BG_DARK, 
                            fg=TEXT_PRIMARY,
                            insertbackground=accent,
                            bd=0,
                            relief=tk.FLAT)
        pos_entry.pack(fill=tk.X)
        pos_entry.insert(0, "3,7")
        
        # Buttons
        btn_frame = tk.Frame(input_card, bg=BG_CARD)
        btn_frame.pack(pady=5)
        
        start_btn = tk.Button(btn_frame, 
                             text="Start Recovery", 
                             font=("Segoe UI", 10, "bold"),
                             bg=accent,
                             fg="#ffffff",
                             padx=25,
                             pady=8,
                             bd=0,
                             cursor="hand2",
                             relief=tk.FLAT,
                             activebackground=accent,
                             activeforeground="#ffffff")
        start_btn.pack(side=tk.LEFT, padx=5)
        
        stop_btn = tk.Button(btn_frame, 
                            text="Stop", 
                            font=("Segoe UI", 10),
                            bg="#21262d",
                            fg=TEXT_PRIMARY,
                            padx=25,
                            pady=8,
                            bd=0,
                            cursor="hand2",
                            relief=tk.FLAT,
                            activebackground="#30363d",
                            activeforeground=TEXT_PRIMARY,
                            state=tk.DISABLED)
        stop_btn.pack(side=tk.LEFT, padx=5)
        
        save_btn = tk.Button(btn_frame, 
                            text="Save Results", 
                            font=("Segoe UI", 10),
                            bg="#3fb950",
                            fg="#ffffff",
                            padx=25,
                            pady=8,
                            bd=0,
                            cursor="hand2",
                            relief=tk.FLAT,
                            activebackground="#2ea043",
                            activeforeground="#ffffff",
                            command=lambda: self.save_results(chain))
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # Progress
        progress = ttk.Progressbar(input_card, mode='determinate', length=700)
        progress.pack(pady=8)
        
        status_label = tk.Label(input_card, 
                               text="Ready to recover your seed phrase", 
                               font=("Segoe UI", 9),
                               bg=BG_CARD,
                               fg=TEXT_SECONDARY)
        status_label.pack()
        
        # Bottom: Results and Console Panels
        bottom_container = tk.Frame(main_container, bg=BG_DARK)
        bottom_container.pack(fill=tk.BOTH, expand=True)
        
        # Results Panel (Left)
        results_card = tk.Frame(bottom_container, bg=BG_CARD)
        results_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        tk.Label(results_card, text="Results:", 
                font=("Segoe UI", 11, "bold"),
                bg=BG_CARD,
                fg=accent,
                padx=15,
                pady=8).pack(anchor=tk.W)
        
        result_text = scrolledtext.ScrolledText(results_card, 
                                               height=10,
                                               font=("Consolas", 10),
                                               bg=BG_DARK,
                                               fg=TEXT_PRIMARY,
                                               insertbackground=accent,
                                               bd=0,
                                               relief=tk.FLAT)
        result_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Console Panel (Right)
        console_card = tk.Frame(bottom_container, bg=BG_CARD)
        console_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        tk.Label(console_card, text="Log Console:", 
                font=("Segoe UI", 11, "bold"),
                bg=BG_CARD,
                fg=TEXT_SECONDARY,
                padx=15,
                pady=8).pack(anchor=tk.W)
        
        console_text = scrolledtext.ScrolledText(console_card, 
                                               height=10,
                                               font=("Consolas", 9),
                                               bg=BG_CONSOLE,
                                               fg="#7ee787",
                                               insertbackground="#7ee787",
                                               bd=0,
                                               relief=tk.FLAT,
                                               state=tk.DISABLED)
        console_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Store references
        setattr(self, f"length_var_{chain}", length_var)
        setattr(self, f"seed_text_{chain}", seed_text)
        setattr(self, f"addr_entry_{chain}", addr_entry)
        setattr(self, f"pos_entry_{chain}", pos_entry)
        setattr(self, f"start_btn_{chain}", start_btn)
        setattr(self, f"stop_btn_{chain}", stop_btn)
        setattr(self, f"progress_{chain}", progress)
        setattr(self, f"status_label_{chain}", status_label)
        setattr(self, f"result_text_{chain}", result_text)
        setattr(self, f"console_text_{chain}", console_text)
        
        # Bind buttons
        start_btn.config(command=lambda: self.start_recovery(chain, accent))
        stop_btn.config(command=self.stop_recovery)
        
        # Initial log message
        self.log(chain, f"[INFO] {chain} tab ready (PRO MODE!)", TEXT_SECONDARY)
        
    def log(self, chain, message, color=TEXT_SUCCESS):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        
        console_text = getattr(self, f"console_text_{chain}")
        console_text.config(state=tk.NORMAL)
        console_text.insert(tk.END, log_line)
        console_text.see(tk.END)
        console_text.config(state=tk.DISABLED)
        
        print(f"[{timestamp}] {message}")
        
    def save_results(self, chain):
        result_text = getattr(self, f"result_text_{chain}")
        content = result_text.get("1.0", tk.END)
        
        if not content.strip():
            messagebox.showwarning("Warning", "No results to save!")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Save Recovery Results"
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Success", f"Results saved to {file_path}")
                self.log(chain, f"Results saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
                self.log(chain, f"Error saving file: {str(e)}", "#f85149")
        
    def start_recovery(self, chain, accent):
        length_var = getattr(self, f"length_var_{chain}")
        seed_text = getattr(self, f"seed_text_{chain}")
        addr_entry = getattr(self, f"addr_entry_{chain}")
        pos_entry = getattr(self, f"pos_entry_{chain}")
        start_btn = getattr(self, f"start_btn_{chain}")
        stop_btn = getattr(self, f"stop_btn_{chain}")
        result_text = getattr(self, f"result_text_{chain}")
        
        target_length = int(length_var.get())
        seed_input = seed_text.get("1.0", tk.END).strip()
        target_addr = addr_entry.get().strip()
        pos_input = pos_entry.get().strip()
        
        self.log(chain, f"Starting recovery for {chain}...")
        self.log(chain, f"Target seed length: {target_length}")
        self.log(chain, f"Missing positions: {pos_input}")
        if target_addr:
            self.log(chain, f"Target address: {target_addr}")
        
        if not seed_input or not pos_input:
            messagebox.showerror("Error", "Please fill in seed phrase and positions!")
            self.log(chain, "ERROR: Fields missing", "#f85149")
            return
        
        try:
            positions = [int(p.strip())-1 for p in pos_input.split(",")]  # 0-based
            if len(positions) < 1 or len(positions) > 5:
                messagebox.showerror("Error", "Please enter 1-5 positions!")
                self.log(chain, "ERROR: Need 1-5 positions", "#f85149")
                return
        except ValueError:
            messagebox.showerror("Error", "Positions must be numbers separated by commas!")
            self.log(chain, "ERROR: Invalid positions format", "#f85149")
            return
        
        seed_words = seed_input.split()
        if len(seed_words) != target_length:
            messagebox.showerror("Error", f"Seed phrase must be {target_length} words!")
            self.log(chain, f"ERROR: Seed length {len(seed_words)} != {target_length}", "#f85149")
            return
        
        # Validate known words are in BIP39 list
        invalid_words = []
        for i, word in enumerate(seed_words):
            if i not in positions and word != '?' and word not in WORD_SET:
                invalid_words.append((i+1, word))
        if invalid_words:
            error_msg = "Invalid BIP39 words found:\n"
            for pos, word in invalid_words:
                error_msg += f"  Position {pos}: '{word}'\n"
            messagebox.showerror("Error", error_msg)
            self.log(chain, "ERROR: Invalid BIP39 words found", "#f85149")
            return
        
        self.log(chain, f"Seed phrase length: {len(seed_words)} words")
        self.is_running = True
        self.current_chain = chain
        start_btn.config(state=tk.DISABLED)
        stop_btn.config(state=tk.NORMAL)
        result_text.delete("1.0", tk.END)
        result_text.insert(tk.END, f"[LOG] Starting recovery for {chain}...\n")
        result_text.insert(tk.END, f"[LOG] Seed length: {target_length} words\n")
        total = len(self.wordlist) ** len(positions)
        result_text.insert(tk.END, f"[LOG] Total combinations to check: {total:,}\n\n")
        
        thread = threading.Thread(target=self.recover_seed, 
                                 args=(seed_words, positions, target_addr, chain, accent))
        thread.daemon = True
        thread.start()
        
    def stop_recovery(self):
        self.log(self.current_chain, "Stop requested by user", "#ffa657")
        self.is_running = False
        
    def recover_seed(self, seed_words, positions, target_addr, chain, accent):
        self.log(chain, f"Starting brute-force (PRO MODE!) for {chain}...")
        
        progress = getattr(self, f"progress_{chain}")
        status_label = getattr(self, f"status_label_{chain}")
        result_text = getattr(self, f"result_text_{chain}")
        start_btn = getattr(self, f"start_btn_{chain}")
        stop_btn = getattr(self, f"stop_btn_{chain}")
        
        # Get Bitcoin-specific options if needed
        path_name = None
        addr_type = None
        if chain == "BTC":
            path_var = getattr(self, f"path_var_{chain}")
            addr_type_var = getattr(self, f"addr_type_var_{chain}")
            path_name = path_var.get()
            addr_type = BTC_ADDRESS_TYPES[addr_type_var.get()]
            self.log(chain, f"Using derivation path: {path_name}")
            self.log(chain, f"Using address type: {addr_type}")
        
        total = len(self.wordlist) ** len(positions)
        progress["maximum"] = total
        count = 0
        found = 0
        matched = 0
        
        self.log(chain, f"Total combinations to check: {total:,}")
        
        # Precompute the seed template as tuple for faster copying
        seed_template = tuple(seed_words)
        
        # Generate all possible combinations of words for missing positions
        for candidate_words in product(WORDLIST, repeat=len(positions)):
            if not self.is_running or (target_addr and matched > 0):
                break
                
            # Create test seed
            test_words = list(seed_template)
            for idx, pos in enumerate(positions):
                test_words[pos] = candidate_words[idx]
            test_seed = " ".join(test_words)
            
            if self.mnemo.check(test_seed):
                found += 1
                self.log(chain, f"Valid seed found (#{found}): {test_seed}")
                
                if target_addr and chain in ["BTC", "ETH", "SOL"]:
                    try:
                        if chain == "BTC":
                            derived_addr = derive_btc_address(test_seed, path_name, addr_type)
                        elif chain == "ETH":
                            derived_addr = derive_eth_address(test_seed)
                        elif chain == "SOL":
                            derived_addr = derive_solana_address(test_seed)
                        
                        if derived_addr == target_addr:
                            matched += 1
                            self.log(chain, f"🎉🎉🎉 MATCHING SEED FOUND! Address matches target!")
                            result_text.insert(tk.END, f"🎉🎉🎉 SEED FOUND (MATCHES ADDRESS)!\n")
                            result_text.insert(tk.END, f"Seed: {test_seed}\n")
                            result_text.insert(tk.END, f"Address: {derived_addr}\n\n")
                            result_text.see(tk.END)
                    except Exception as e:
                        self.log(chain, f"Error deriving address: {e}", "#f85149")
                else:
                    result_text.insert(tk.END, f"✅ Valid seed (#{found}):\n")
                    result_text.insert(tk.END, f"{test_seed}\n\n")
                    result_text.see(tk.END)
            
            count += 1
            if count % 10000 == 0:
                progress["value"] = count
                if matched > 0:
                    status_label.config(text=f"Checking: {count:,}/{total:,} | Found: {found} | Matched: {matched}")
                else:
                    status_label.config(text=f"Checking: {count:,}/{total:,} | Found: {found}")
                self.root.update_idletasks()
        
        self.is_running = False
        start_btn.config(state=tk.NORMAL)
        stop_btn.config(state=tk.DISABLED)
        
        final_msg = f"Complete! Found {found} valid seeds, {matched} matching target address."
        status_label.config(text=final_msg)
        result_text.insert(tk.END, f"\n[LOG] {final_msg}\n")
        
        self.log(chain, final_msg)
        self.log(chain, "="*60)

if __name__ == "__main__":
    root = tk.Tk()
    app = MultiChainSeedRecovery(root)
    root.mainloop()
