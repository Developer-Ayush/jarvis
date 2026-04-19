#!/usr/bin/env python3
"""
patch_oscrypto.py — Run at build time on Vercel to fix oscrypto OpenSSL 3.x regex.
Called by vercel.json buildCommand.
"""
import site, os, re, sys

patched = False
search_dirs = site.getsitepackages() + [site.getusersitepackages()]

for s in search_dirs:
    f = os.path.join(s, "oscrypto/_openssl/_libcrypto_cffi.py")
    if os.path.exists(f):
        with open(f) as fp:
            content = fp.read()
        old = r"version_match = re.search('\\b(\\d\\.\\d\\.\\d[a-z]*)\\b', version_string)"
        new = r"version_match = re.search('\\b(\\d+\\.\\d+\\.\\d+[a-z]*)\\b', version_string)"
        if old in content:
            content = content.replace(old, new, 1)
            with open(f, "w") as fp:
                fp.write(content)
            print(f"✅ oscrypto patched at: {f}")
            patched = True
        else:
            print(f"ℹ️  oscrypto already patched or pattern not found at: {f}")
            patched = True
        break

if not patched:
    print("⚠️  oscrypto file not found — may cause ask_sdk import failure")
    sys.exit(0)  # don't fail the build, let it try
