# Wallet-py3k

Python library to read/write [Apple Wallet](http://developer.apple.com/library/ios/#documentation/UserExperience/Conceptual/PassKit_PG/Chapters/Introduction.html#//apple_ref/doc/uid/TP40012195-CH1-SW1) (.pkpass) files

This is a fork of https://github.com/ofw/wallet-py3k which does not suits my needs


## New Features
  * Direct Generation of passes without thee need to store them on a filesystem (if wanted)
  * Password less Keys possible if wanted
  * Validation of Fields and Passes including own Exception (PassParameterException)
  * Complete Refactored and Simplified Code


## ToDos
  * Update of Getting Started
  * Full Example including which Fields are Possible


## Old: Getting Started
This part from here needs to be updated:

1. Create a Pass Type Id:
    1. Visit the [Visit the iOS Provisioning Portal](https://developer.apple.com/account/resources/certificates/list)
    2. On the left, click Identifiers
    3. From the type drop-down on the right, choose Pass Type IDs
    4. Next to Identifiers, click the + (plus) button.
    5. Select Pass Type IDs and click Continue
    6. Enter a description and an identifier (typically in the form `pass.com.yourcompany.some_name`) and click Continue
    7. Download the generated file
2. Double-click the pass file you downloaded to install it to your keychain
3. Export the pass certificate as a p12 file:
    1. Open Keychain Access
    2. Locate the pass certificate -- it should be under the login keychain, Certificates category.
    3. Right-click the pass and choose Export
    4. Make sure the File Format is set to Personal Information Exchange (.p12) and export to a convenient location.
4. Generate the necessary certificate and key .pem files
    1. Open Terminal and navigate to the folder where you exported the p12 file.
    2. Generate the pass pem file:

       ```sh
       openssl pkcs12 -in "Certificates.p12" -clcerts -nokeys -out certificate.pem --legacy
       ```
    3. Generate the key pem file:<br/>**Note** *you must set a password for the key pem file or you'll get errors when attempt to generate the pkpass file.*

       ```sh
       openssl pkcs12 -in "Certificates.p12" -nocerts -out key.pem
       ```
5. Generate the pem file for the Apple WWDR certificate (available from [developer.apple.com](http://developer.apple.com/certificationauthority/AppleWWDRCA.cer)) following the same steps as above.
6. Move all the pem files into your project


## Typical Usage

```python
    from wallet.models import Pass, Barcode, StoreCard

    pass_type_identifier = "pass.com.yourcompany.some_name"
    team_identifier = "ABCDE1234"  # Your Apple team ID
    cert_pem = "certficate.pem"
    key_pem = "key.pem"
    wwdr_pem = "AppleWWDRCA.pem"
    key_pem_password = "your_password"

    cardInfo = StoreCard()
    cardInfo.addPrimaryField('name', 'John Doe', 'Name')

    passfile = Pass(cardInfo,
                    passTypeIdentifier=cls.pass_type_identifier,
                    organizationName=cls.organization_name,
                    teamIdentifier=cls.team_identifier)

    # charge_response.id is trackable via the Stripe dashboard
    passfile.serialNumber = charge_response.id
    passfile.barcode = Barcode(message = charge_response.id, format=BarcodeFormat.PDF417)
    passfile.description = charge_response.description 

    # Including the icon and logo is necessary for the passbook to be valid.
    passfile.addFile("icon.png", open("icon.png", "rb"))
    passfile.addFile("logo.png", open("logo.png", "rb"))
    _ = passfile.create(cls.cert_pem,
                        cls.key_pem,
                        cls.wwdr_pem,
                        cls.key_pem_password,
                        "pass_name.pkpass")

```

### Notes

* You must use a password for your key.pem file. If you don't, the pass file won't be properly generated. You'll probably see errors like `PEM routines:PEM_read_bio:no start line` in your server's logs.
* `passfile.create()` writes the pass file to your server's filesystem. By default, it's written to the same directory as your script, but you can pass an absolute path (including the file name) to store elsewhere.
* `passfile.create()` returns the name of the generated file, which matches what you pass to it as the fifth parameter.
* Valid `cardInfo` constructors mirror the pass types defined by Apple. For example, `StoreCard()`, `BoardingPass()`, `Coupon()`, etc.
* The various "add field" methods (e.g. `addPrimaryField()`) take three unnamed parameters in the order `key`, `value`, `label`

An example Flask route handler to return the generated pass files:

```python
@application.route("/passes/<path:fname>")
def passes_proxy(fname):
    """static passes serve"""
    return send_from_directory("passes", fname, mimetype="application/vnd.apple.pkpass")
```

An example usage in a React app using Stripe and Stripe Elements to process payments and generate a store pass:

```javascript
paymentRequest.on('token', async (ev) => {
  try {
    const response = await fetch('https://your_server/charge', {
      method: 'POST',
      body: JSON.stringify({
        token: ev.token.id,
        amount: totalInCents,
        description: purchasedItems.join(',\n')
      }),
      headers: {'content-type': 'application/json'},
    });
    if (!response.ok) {
      throw new Error('There was a problem processing your payment.');
    }
    // Report to the browser that the payment was successful, prompting
    // it to download the pass file to the user's Wallet
    ev.complete('success');
    const pkpass = await response.json();
    window.location.href = `https://your_server/passes/${pkpass.filename}`;
  } catch (error) {
    throw new Error("There was a problem processing your payment.");
  }
});
```
