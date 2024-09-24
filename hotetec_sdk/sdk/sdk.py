import requests

from hotetec_sdk import config


class HotetecSDK:
    URI = 'https://hotel.hotetec.com/publisher/xmlservice.srv'
    AGENCY_CODE = config.HOTETEC_CONFIG.get('AGENCY_CODE')
    USERNAME = config.HOTETEC_CONFIG.get('USERNAME')
    PASSWORD = config.HOTETEC_CONFIG.get('PASSWORD')
    LANGUAGE = 'ES'
    SYSTEM_CODE = 'XML'
    HEADERS = {'Content-Type': 'application/xml'}

    def authenticate(self):
        xml_data = f"""
            <SesionAbrirPeticion>
                <codsys>{self.SYSTEM_CODE}</codsys>
                <codage>{self.AGENCY_CODE}</codage>
                <idtusu>{self.USERNAME}</idtusu>
                <pasusu>{self.PASSWORD}</pasusu>
                <codidi>{self.LANGUAGE}</codidi>
            </SesionAbrirPeticion>
        """
        response = requests.post(self.URI, data=xml_data, headers=self.HEADERS)

        if response.status_code == 200:
            print(response.text)
        else:
            raise f'Error: {response.status_code}'
