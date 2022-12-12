""" Apple Passbook """
# pylint: disable=too-few-public-methods, too-many-instance-attributes
import decimal
import hashlib
from io import BytesIO
import json
import subprocess
import zipfile
import re
import tempfile

from .exceptions import PassParameterException


def check_subfields(fields):
    """ Check the fields insised a field list """
    for field in fields:
        date = field.get('dateStyle')
        time = field.get('timeStyle')
        regex \
            = r'^(-?(?:[1-9][0-9]*)?[0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])T(2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])(\.[0-9]+)?(Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$'
        # need none here because of db model default
        if date or time:
            match_iso8601 = re.compile(regex).match
            if match_iso8601(field['value']) is None:
                raise PassParameterException("Date does not match iso8601 format")

def field_checks(field_name, field_data):
    """ Check Field Contents if the valid """
    if field_name == 'webServiceURL':
        if not field_data.startswith('https://'):
            raise PassParameterException("Webservie Url need to start with https://")

    if field_name == 'serialNumber':
        if not isinstance(field_data, str):
            raise PassParameterException("Serial Needs to be a String")
        if len(field_data) <= 16:
            raise PassParameterException("Serial Number to Short")

    if field_name == 'headerFields':
        if len(field_data) > 3:
            raise PassParameterException("To many Header Fields (>3)")
        check_subfields(field_data)

    if field_name == 'primaryFields':
        check_subfields(field_data)

    if field_name == 'secondaryFields':
        check_subfields(field_data)

    if field_name == 'auxiliaryFields':
        check_subfields(field_data)

    if field_name == 'backFields':
        check_subfields(field_data)

class Alignment():
    """ Text Alignment """
    LEFT = 'PKTextAlignmentLeft'
    CENTER = 'PKTextAlignmentCenter'
    RIGHT = 'PKTextAlignmentRight'
    JUSTIFIED = 'PKTextAlignmentJustified'
    NATURAL = 'PKTextAlignmentNatural'


class BarcodeFormat():
    """ Barcode Format"""
    PDF417 = 'PKBarcodeFormatPDF417'
    QR = 'PKBarcodeFormatQR'
    AZTEC = 'PKBarcodeFormatAztec'
    CODE128 = 'PKBarcodeFormatCode128'


class TransitType():
    """ Transit Type for Boarding Passes """
    AIR = 'PKTransitTypeAir'
    TRAIN = 'PKTransitTypeTrain'
    BUS = 'PKTransitTypeBus'
    BOAT = 'PKTransitTypeBoat'
    GENERIC = 'PKTransitTypeGeneric'


class DateStyle():
    """ Date Style """
    NONE = 'PKDateStyleNone'
    SHORT = 'PKDateStyleShort'
    MEDIUM = 'PKDateStyleMedium'
    LONG = 'PKDateStyleLong'
    FULL = 'PKDateStyleFull'


class NumberStyle():
    """ Number Style """
    DECIMAL = 'PKNumberStyleDecimal'
    PERCENT = 'PKNumberStylePercent'
    SCIENTIFIC = 'PKNumberStyleScientific'
    SPELLOUT = 'PKNumberStyleSpellOut'

class Field():
    """ Wallet Text Field"""

    def __init__(self, **kwargs):
        """
         Initiate Field

        :param key: The key must be unique within the scope
        :param value: Value of the Field
        :param attributed_value: Optional. Attributed value of the field.
        :param label: Optional Label Text for field
        :param change_message: Optional. String that is displayed when the pass is updated
        :param text_alignment: left/ center/ right, justified, natural
        :return: Nothing

        """
        # pylint: disable=invalid-name
        self.key = kwargs['key']
        if 'attributed_value' in kwargs:
            self.attributedValue = kwargs['attributed_value']
        self.value = kwargs['value']
        self.label = kwargs.get('label', '')
        if 'change_message' in kwargs:
            self.changeMessage = kwargs['change_message'] # Don't Populate key if not needed
        self.textAlignment = {
            'left': Alignment.LEFT,
            'center': Alignment.CENTER,
            'right': Alignment.RIGHT,
            'justified': Alignment.JUSTIFIED,
            'natural': Alignment.NATURAL,
        }.get(kwargs.get('text_alignment', 'left'))

    def json_dict(self):
        """ Return dict object from class """
        return self.__dict__


class DateField(Field):
    """ Wallet Date Field """

    def __init__(self, **kwargs):
        """
        Initiate Field

        :param key: The key must be unique within the scope
        :param value: Value of the Field
        :param label: Optional Label Text for field
        :param change_message: Optional. String that is displayed when the pass is updated
        :param text_alignment: left/ center/ right, justified, natural
        :param date_style: none/short/medium/long/full
        :param time_style: none/short/medium/long/full
        :param is_relativ: True/False
        """
        #pylint: disable=invalid-name

        super(DateField, self).__init__(**kwargs)
        styles = {
            "none": DateStyle.NONE,
            "short": DateStyle.SHORT,
            "medium": DateStyle.MEDIUM,
            "long": DateStyle.LONG,
            "full": DateStyle.FULL,
        }

        self.dateStyle = styles.get(kwargs.get('date_style', 'short'))
        self.timeStyle = styles.get(kwargs.get('time_style', 'short'))
        self.isRelative = kwargs.get('is_relativ', False)

    def json_dict(self):
        """ Return dict object from class """
        return self.__dict__


class NumberField(Field):
    """ Number Field """

    def __init__(self, **kwargs):
        """
        Initiate Field

        :param key: The key must be unique within the scope
        :param value: Value of the Field
        :param label: Optional Label Text for field
        :param change_message: Optional. String that is displayed when the pass is updated
        :param text_alignment: left/ center/ right, justified, natural
        :param number_style: decimal/percent/scientific/spellout.
        """
        #pylint: disable=invalid-name

        super(NumberField, self).__init__(**kwargs)
        self.numberStyle = {
            'decimal' : NumberStyle.DECIMAL,
            'percent' : NumberStyle.PERCENT,
            'scientific' : NumberStyle.SCIENTIFIC,
            'spellout' : NumberStyle.SPELLOUT,
        }.get(kwargs.get('number_style', 'decimal'))
        self.value = float(self.value)

    def json_dict(self):
        """ Return dict object from class """
        return self.__dict__


class CurrencyField(Field):
    """ Currency Field """

    def __init__(self, **kwargs):
        """
        Initiate Field

        :param key: The key must be unique within the scope
        :param value: Value of the Field
        :param label: Optional Label Text for field
        :param change_message: Optional. String that is displayed when the pass is updated
        :param text_alignment: left/ center/ right, justified, natural
        :param currency_code: ISO 4217 currency Code
        """
        #pylint: disable=invalid-name

        super(CurrencyField, self).__init__(**kwargs)
        self.currencyCode = kwargs['currency_code']
        self.value = float(self.value)

    def json_dict(self):
        """ Return dict object from class """
        return self.__dict__


class Barcode():
    """
    Barcode Field
    """

    def __init__(self, **kwargs):
        """
        Initiate Field

        :param message: Message or Payload for Barcdoe
        :param format: pdf417 / qr/ aztec / code128
        :param encoding: Default utf-8
        :param alt_text: Optional Text displayed near the barcode
        """

        #pylint: disable=invalid-name
        self.format = {
            'pdf417' : BarcodeFormat.PDF417,
            'qr' : BarcodeFormat.QR,
            'aztec' : BarcodeFormat.AZTEC,
            'code128' : BarcodeFormat.CODE128,
        }.get(kwargs['format'], 'qr')
        self.message = kwargs['message']
        self.messageEncoding = kwargs.get('encoding', 'iso-8859-1')
        self.altText = kwargs.get('alt_text', '')

    def json_dict(self):
        """ Return dict object from class """
        return self.__dict__


class Location():
    """
    Pass Location Object
    """

    def __init__(self, **kwargs):
        """
        Fill Location Object.

        :param latitude: Latitude Float
        :param longitude: Longitude Float
        :param altitude: optional
        :param distance: optional
        :param relevant_text: optional
        :return: Nothing

        """
        # pylint: disable=invalid-name

        for name in ['latitude', 'longitude', 'altitude']:
            try:
                setattr(self, name, float(kwargs[name]))
            except (ValueError, TypeError, KeyError):
                setattr(self, name, 0.0)
        if 'distance' in kwargs:
            self.distance = kwargs['distance']
        self.relevantText = kwargs.get('relevant_text', '')

    def json_dict(self):
        """ Return dict object from class """
        return self.__dict__


class IBeacon():
    """ iBeacon """

    def __init__(self, **kwargs):
        """
        Create Beacon
        :param proximity_uuid:
        :param major:
        :param minor:
        :param relevant_text: Option Text shown when near the ibeacon
        """
        # pylint: disable=invalid-name

        self.proximityUUID = kwargs['proximity_uuid']
        self.major = kwargs['major']
        self.minor = kwargs['minor']

        self.relevantText = kwargs.get('relevant_text', '')

    def json_dict(self):
        """ Return dict object from class """
        return self.__dict__


class PassInformation():
    """
    Basis Fields for Wallet Passes
    """

    def __init__(self):
        # pylint: disable=invalid-name
        self.headerFields = []
        self.primaryFields = []
        self.secondaryFields = []
        self.backFields = []
        self.auxiliaryFields = []

    def add_header_field(self, **kwargs):
        """
        Add Simple Field to Header
        :param key:
        :param value:
        :param label: optional
        """
        self.headerFields.append(Field(**kwargs))

    def add_primary_field(self, **kwargs):
        """
        Add Simple Primary Field
        :param key:
        :param value:
        :param label: optional
        """
        self.primaryFields.append(Field(**kwargs))

    def add_secondary_field(self, **kwargs):
        """
        Add Simple Secondary Field
        :param key:
        :param value:
        :param label: optional
        """
        self.secondaryFields.append(Field(**kwargs))

    def add_back_field(self, **kwargs):
        """
        Add Simple Back Field
        :param key:
        :param value:
        :param label: optional
        """
        self.backFields.append(Field(**kwargs))

    def add_auxiliary_field(self, **kwargs):
        """
        Add Simple Auxilary Field
        :param key:
        :param value:
        :param label: optional
        """
        self.auxiliaryFields.append(Field(**kwargs))

    def json_dict(self):
        """
        Create Json object of all Fields
        """
        data = {}
        for what in ['headerFields', 'primaryFields', 'secondaryFields',
                     'backFields', 'auxiliaryFields']:
            if hasattr(self, what):
                field_data = [f.json_dict() for f in getattr(self, what)]
                field_checks(what, field_data)
                data.update({what: field_data})
        return data


class BoardingPass(PassInformation):
    """ Wallet Boarding Pass """

    def __init__(self, transitType=TransitType.AIR):
        #pylint: disable=invalid-name
        super(BoardingPass, self).__init__()
        self.transitType = transitType
        self.jsonname = 'boardingPass'

    def json_dict(self):
        data = super(BoardingPass, self).json_dict()
        data.update({'transitType': self.transitType})
        return data


class Coupon(PassInformation):
    """ Wallet Coupon Pass """

    def __init__(self):
        super(Coupon, self).__init__()
        self.jsonname = 'coupon'


class EventTicket(PassInformation):
    """ Wallet Event Ticket """

    def __init__(self):
        super(EventTicket, self).__init__()
        self.jsonname = 'eventTicket'


class Generic(PassInformation):
    """ Wallet Generic Pass """

    def __init__(self):
        super(Generic, self).__init__()
        self.jsonname = 'generic'


class StoreCard(PassInformation):
    """ Wallet Store Card """

    def __init__(self):
        super(StoreCard, self).__init__()
        self.jsonname = 'storeCard'


class Pass():
    """ Apple Wallet Pass Object """

    def __init__(self, **kwargs):
        """
        Prepare Pass
        :params pass_information:
        :params pass_type_identifier:
        :params organization_name:
        :params team_identifier:
        """

        #pylint: disable=invalid-name

        self._files = {}  # Holds the files to include in the .pkpass
        self._hashes = {}  # Holds the SHAs of the files array

        # Standard Keys

        # Required. Team identifier of the organization that originated and
        # signed the pass, as issued by Apple.
        self.teamIdentifier = kwargs['team_identifier']
        # Required. Pass type identifier, as issued by Apple. The value must
        # correspond with your signing certificate. Used for grouping.
        self.passTypeIdentifier = kwargs['pass_type_identifier']
        # Required. Display name of the organization that originated and
        # signed the pass.
        self.organizationName = kwargs['organization_name']
        # Required. Serial number that uniquely identifies the pass.
        self.serialNumber = ''
        # Required. Brief description of the pass, used by the iOS
        # accessibility technologies.
        self.description = ''
        # Required.
        self.formatVersion = 1

        # Visual Appearance Keys
        self.backgroundColor = None  # Optional. Background color of the pass
        self.foregroundColor = None  # Optional. Foreground color of the pass,
        self.labelColor = None  # Optional. Color of the label text
        self.logoText = None  # Optional. Text displayed next to the logo
        self.barcode = None  # Optional. Information specific to barcodes.
        self.barcodes = []

        # Optional. If true, the strip image is displayed
        self.suppressStripShine = False

        # Web Service Keys

        # Optional. If present, authenticationToken must be supplied
        self.webServiceURL = None
        # The authentication token to use with the web service
        self.authenticationToken = None

        # Relevance Keys

        # Optional. Locations where the pass is relevant.
        # For example, the location of your store.
        self.locations = []
        # Optional. IBeacons data
        self.ibeacons = []
        # Optional. Date and time when the pass becomes relevant
        self.relevantDate = None

        # Optional. A list of iTunes Store item identifiers for
        # the associated apps.
        self.associatedStoreIdentifiers = None
        self.appLaunchURL = None
        # Optional. Additional hidden data in json for the passbook
        self.userInfo = None

        self.exprirationDate = None
        self.voided = None

        self.passInformation = kwargs['pass_information']

    def add_file(self, name, file_handle):
        """
        Add file to the file
        :params name: String name
        :params file_handle: File Handle
        """
        self._files[name] = file_handle.read()

    # Creates the actual .pkpass file
    def create(self, certificate, key, wwdr_certificate, password=False, file_name=None, filemode=True):
        """
        Create .pkass File
        """
        # pylint: disable=too-many-arguments
        pass_json = self._create_pass_json()
        manifest = self._create_manifest(pass_json)
        signature = self._create_signature(manifest, certificate, key, wwdr_certificate, password, filemode)
        if not file_name:
            file_name = BytesIO()
        datei = self._create_zip(pass_json, manifest, signature, file_name=file_name)
        return datei

    def _create_pass_json(self):
        """
        Create Json Pass Files
        """
        return json.dumps(self, default=pass_handler).encode('utf-8')

    def _create_manifest(self, pass_json):
        """
        Creates the hashes for the files and adds them
        into a json string
        """
        # Creates SHA hashes for all files in package
        self._hashes['pass.json'] = hashlib.sha1(pass_json).hexdigest()
        for filename, filedata in self._files.items():
            self._hashes[filename] = hashlib.sha1(filedata).hexdigest()
        return json.dumps(self._hashes).encode('utf-8')

    def _create_signature(self, manifest, certificate, key,
                          wwdr_certificate, password, filemode):
        """ Create and Save Signature """
        # pylint: disable=no-self-use, too-many-arguments
        if not filemode:
            #Use Tempfile
            cert_file = tempfile.NamedTemporaryFile(mode='w')
            cert_file.write(certificate)
            cert_file.flush()
            key_file = tempfile.NamedTemporaryFile(mode='w')
            key_file.write(key)
            key_file.flush()
            wwdr_file = tempfile.NamedTemporaryFile(mode='w')
            wwdr_file.write(wwdr_certificate)
            wwdr_file.flush()
            certificate = cert_file.name
            key = key_file.name
            wwdr_certificate = wwdr_file.name

        openssl_cmd = [
            'openssl',
            'smime',
            '-binary',
            '-sign',
            '-certfile',
            wwdr_certificate,
            '-signer',
            certificate,
            '-inkey',
            key,
            '-outform',
            'DER',
            '-passin',
            'pass:{}'.format(password),
        ]

        process = subprocess.Popen(
            openssl_cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )
        process.stdin.write(manifest)
        der, error = process.communicate()
        if process.returncode != 0:
            raise Exception(error)

        return der


    # Creates .pkpass (zip archive)
    def _create_zip(self, pass_json, manifest, signature, file_name=None):
        """
        Creats .pkass ZIP Archive
        """
        z_file = zipfile.ZipFile(file_name or 'pass.pkpass', 'w')
        z_file.writestr('signature', signature)
        z_file.writestr('manifest.json', manifest)
        z_file.writestr('pass.json', pass_json)
        for filename, filedata in self._files.items():
            z_file.writestr(filename, filedata)
        z_file.close()
        return file_name


    def json_dict(self):
        """
        Return Pass as JSON Dict
        """
        simple_fields = [
            'description',
            'formatVersion',
            'organizationName',
            'passTypeIdentifier',
            'serialNumber',
            'teamIdentifier',
            'suppressStripShine'
            'relevantDate',
            'backgroundColor',
            'foregroundColor',
            'labelColor',
            'logoText',
            'ibeacons',
            'userInfo',
            'voided',
            'associatedStoreIdentifiers',
            'appLaunchURL',
            'exprirationDate',
            'webServiceURL',
            'authenticationToken',
        ]
        data = {}
        data[self.passInformation.jsonname] = self.passInformation.json_dict()
        for field in simple_fields:
            if hasattr(self, field):
                content = getattr(self, field)
                if content:
                    field_checks(field, content)
                    data[field] = content

        if self.barcodes:
            data['barcodes'] = []
            for barcode in self.barcodes:
                data['barcodes'].append(barcode.json_dict())

        if self.locations:
            data['locations'] = []
            for location in self.locations:
                data['locations'].append(location.json_dict())
            if len(data['locations']) >= 10:
                raise PassParameterException("Field locations has more then 10 entries")

        if self.ibeacons:
            data['ibeacons'] = []
            for ibeacon in self.ibeacons:
                data['ibeacons'].append(ibeacon.json_dict())

        requied_fields = [
            'description', 'formatVersion',
            'organizationName', 'organizationName',
            'serialNumber', 'teamIdentifier'
        ]
        for field in requied_fields:
            if field not in data:
                raise PassParameterException("Field {} missing".format(field))
        return data


def pass_handler(obj):
    """ Pass Handler """
    if hasattr(obj, 'json_dict'):
        return obj.json_dict()
    # For Decimal latitude and logitude etc.
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    return obj
