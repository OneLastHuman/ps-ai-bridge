# TCP Protocol - Remote Connections

**Connection** `howDoesItWork.html:42` TCP 49494, Bonjour `_photoshopserver._tcp`.

**Message** `PhotoshopProtocol.java:30`:
```
4B length (incl. after) | 4B com_status 0=encrypted | 4B version 1 | 4B txn | 4B type | payload(encrypted)
```
`type`: 1 error 2 JavaScript 3 Image 5 Data. Image: `1B format 1=JPEG 2=Pixmap + bytes`.

**Encryption** `PSCryptor.cpp:379` PBKDF2-HMAC-SHA1 salt `Adobe Photoshop` iter 1000 key 24 + 3DES/CBC/PKCS5 IV 0.

**JSX** send `stringIDToTypeID("sendDocumentThumbnailToNetworkClient")` with width/height/format. Recv `kPSNetImage`.

**Place image** `imagesandprofiles.html:64` send `B format + JPEG bytes` as `IMAGE_TYPE` -> PS new document.

**Events** `howDoesItWork.html:133` `networkEventSubscribe` for `foregroundColorChanged/toolChanged/closedDocument/documentChanged`.

See `scripts/ps_bridge.py:80` for Python port.
