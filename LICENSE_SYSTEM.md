# VERA Office License System

## Quick Start

### For Customers

#### Get Your Device Fingerprint
```bash
python tools/show_device_fingerprint.py
```
Send this to receive your license.

#### Activate License

**Option 1: USB Stick (Recommended)**
1. Put `vera-license.key` on USB stick (root or `VERA/` folder)
2. Plug USB into computer
3. VERA auto-detects and activates
4. License file is deleted from USB (one-time use)

**Option 2: Manual**
1. Copy `license.key` to `C:\Jarvix\vera-office\data\license.key`
2. Restart VERA Office

---

## For License Administrators

### First-Time Setup

1. **Generate Keys** (one-time):
   ```bash
   python tools/generate_keys.py
   ```
   
   Creates:
   - `backend/core/keys/private_key.pem` (KEEP SECRET!)
   - `backend/core/keys/public_key.pem` (ships with app)

### Create License

1. **Get customer's device fingerprint** (they run `show_device_fingerprint.py`)

2. **Create license:**
   ```bash
   python tools/create_license.py \
     --device <FINGERPRINT> \
     --plan professional \
     --days 365 \
     --customer "Company Name" \
     --output customer-license.key
   ```

3. **Send `.key` file** to customer (email or USB stick)

### Plans Available

- `trial` - 30 days, 100 documents, free
- `basic` - 5,000 documents, €29/month
- `professional` - Unlimited, €59/month
- `enterprise` - Unlimited + support, €99/month

### Verify License

```bash
python tools/verify_license.py
```

---

## Security

### Copy Protection
- License is bound to device hardware (CPU, MAC, Disk Serial)
- Cannot be copied to another computer
- Encrypted with AES-256-GCM (device-specific key)

### Signature Verification
- RSA-4096 digital signatures
- Tampering detection
- Only licenses signed with private key are valid

### Key Safety
- **Private Key:** Store securely, backup offline, NEVER commit to git
- **Public Key:** Ships with app, used for verification only
- **Loss of private key = ALL licenses invalidated**

---

## Troubleshooting

### "Public key not found"
Run: `python tools/generate_keys.py`

### "Device fingerprint mismatch"
License was created for different device. Get correct fingerprint and create new license.

### "Decryption failed"
License file is for different device or corrupted.

---

## Documentation

- Full upgrade details: `CRYPTO_UPGRADE.md`
- Server tools: `tools/README.md`
- License API: `backend/api/license_api.py`
