from datetime import datetime

import requests
import xmltodict

from hotetec_sdk.entities.hotel import Hotel
from hotetec_sdk.entities.room import Room
from hotetec_sdk.entities.room_service import RoomService
from hotetec_sdk.entities.cancellation_restriction import CancellationRestriction

from hotetec_sdk import config


class HotetecSDK:
    URI = 'https://hotel.hotetec.com/publisher/xmlservice.srv'
    AGENCY_CODE = config.HOTETEC_CONFIG.get('AGENCY_CODE')
    USERNAME = config.HOTETEC_CONFIG.get('USERNAME')
    PASSWORD = config.HOTETEC_CONFIG.get('PASSWORD')
    SYSTEM_CODE = 'XML'
    HEADERS = {'Content-Type': 'application/xml'}
    CURRENCY = 'USD'
    TOKEN = None
    LANGUAGE = None

    def __init__(self, lang='es'):
        self.LANGUAGE = lang.upper()
        self.authenticate()

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
            try:
                xml_dict = xmltodict.parse(response.text)
                self.TOKEN = xml_dict.get('SesionAbrirRespuesta', {}).get('ideses', None)
            except Exception as e:
                print(f'Error: {e}')
        else:
            raise f'Error: {response.status_code}'

    def availability(self, start_date, end_date, zone_code, distributions):
        if type(start_date) is datetime.date:
            start_date = format(start_date, 'dd/mm/YYYY')
        if type(end_date) is datetime.date:
            start_date = format(end_date, 'dd/mm/YYYY')

        distributions_str = ''
        for index, dist in enumerate(distributions):
            distributions_str += f"""
                <distri id="{index + 1}">
                    <numuni>1</numuni>
                    <numadl>{dist.get('adults', 0) or 0}</numadl>
                    <numnin>{dist.get('children', 0) or 0}</numnin>
                </distri>
            """

        xml_data = f"""
            <DisponibilidadHotelPeticion>
                <ideses>{self.TOKEN}</ideses>
                <codtou>HTI</codtou>
                <fecini>{start_date}</fecini>
                <fecfin>{end_date}</fecfin>
                <codzge>{zone_code}</codzge>
                {distributions_str}
                <chkscm>S</chkscm>
                <coddiv>{self.CURRENCY}</coddiv>
            </DisponibilidadHotelPeticion>
        """
        print(xml_data)
        response = requests.post(self.URI, data=xml_data, headers=self.HEADERS)

        if response.status_code == 200:
            try:
                xml_dict = xmltodict.parse(response.text)

                response = xml_dict.get('DisponibilidadHotelRespuesta')

                if response.get('coderr'):
                    return {'error': {'code': response.get('coderr'), 'text': response.get('txterr')}}

                hotels_data = response.get('infhot')
                if type(hotels_data) is dict:
                    hotels_data = [hotels_data]

                hotels = []
                for hotel in hotels_data:
                    availability = {}
                    rooms_data = hotel.get('infhab', []) or []
                    for room in rooms_data:
                        if room.get('@id') and room.get('@refdis') and room.get('cupest') in ['DS']:
                            availability[room.get('@refdis')] = []

                            cancellation_restrictions = None
                            cancellation_data = room.get('rstcan', {}) or {}
                            if cancellation_data:
                                date = cancellation_data.get('feccan')
                                if date:
                                    date = datetime.strptime(date, '%d/%m/%Y')

                                cancellation_restrictions = CancellationRestriction(
                                    date=date,
                                    percent=float(cancellation_data.get('porcan', '0') or '0'),
                                    amount=float(cancellation_data.get('impcan', '0') or '0'),
                                    text=cancellation_data.get('txtinf'),
                                )

                            availability[room.get('@refdis')].append(Room(
                                room_id=room.get('@id'),
                                distribution=room.get('@refdis'),
                                max_people=int(room.get('capmax', '0') or '0'),
                                min_people=int(room.get('capmin', '0') or '0'),
                                adults_max=int(room.get('adlmax', '0') or '0'),
                                children_max=int(room.get('ninmax', '0') or '0'),
                                base_amount=float(room.get('impbas', '0') or '0'),
                                iva_amount=float(room.get('impiva', '0') or '0'),
                                tax_amount=float(room.get('imptax', '0') or '0'),
                                services=[RoomService(
                                    reference=service.get('refnot'),
                                    name=service.get('txtinf')
                                ) for service in room.get('notser', []) or []],
                                cancellation_restrictions=cancellation_restrictions,
                                non_commissionable_amount=float(room.get('impnoc', '0') or '0'),
                                commissionable_amount=float(room.get('impcom', '0') or '0'),
                                fare_code=room.get('codtrf'),
                                fare_name=room.get('nomtrf'),
                            ))

                    hotels.append(Hotel(
                        name=hotel.get('nomser'),
                        category=hotel.get('codsca'),
                        services=hotel.get('codcas', []) or [],
                        code=hotel.get('codser'),
                        availability=availability,
                    ))

                return {'availability': hotels}

            except Exception as e:
                return {'error': {'code': 500, 'text': 'Unknown error'}}
        else:
            return {'error': {'code': 500, 'text': 'Unknown error'}}
