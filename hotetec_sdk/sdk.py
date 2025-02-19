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

    def __init__(self, token=None, lang='es'):
        self.LANGUAGE = lang.upper()
        if not token:
            self.authenticate()
        else:
            self.TOKEN = token

    def authenticate(self):
        json_data = {
            'SesionAbrirPeticion': {
                'codsys': self.SYSTEM_CODE,
                'codage': self.AGENCY_CODE,
                'idtusu': self.USERNAME,
                'pasusu': self.PASSWORD,
                'codidi': self.LANGUAGE,
            }
        }
        xml_data = xmltodict.unparse(json_data, pretty=True, full_document=False)
        response = requests.post(self.URI, data=xml_data, headers=self.HEADERS)

        if response and response.status_code == 200:
            try:
                xml_dict = xmltodict.parse(response.text)
                self.TOKEN = xml_dict.get('SesionAbrirRespuesta', {}).get('ideses', None)
                return self.TOKEN
            except Exception as e:
                Exception(f'Error: {e}')
        else:
            raise Exception(f'Error: {response}')

    def availability(self, start_date, end_date, zone_code, distributions):
        if type(start_date) is datetime.date:
            start_date = format(start_date, 'dd/mm/YYYY')
        if type(end_date) is datetime.date:
            start_date = format(end_date, 'dd/mm/YYYY')

        json_data = {
            'DisponibilidadHotelPeticion': {
                'ideses': self.TOKEN,
                'codtou': 'HTI',
                'fecini': start_date,
                'fecfin': end_date,
                'codzge': zone_code,
                'chkscm': 'S',
                'distri': [{
                    '@id': index + 1,
                    'numuni': 1,
                    'numadl': dist.get('adults', 0) or 0,
                    'numnin': dist.get('children', 0) or 0,
                    'edanin': dist.get('children_ages', [])
                } for index, dist in enumerate(distributions)],
                'coddiv': self.CURRENCY
            }
        }

        xml_data = xmltodict.unparse(json_data, pretty=True, full_document=False)
        response = requests.post(self.URI, data=xml_data, headers=self.HEADERS)

        print('XML REQUEST', xml_data)

        if response and response.status_code == 200:
            try:
                xml_dict = xmltodict.parse(response.text)
                print('XML RESPONSE', response.text)
                response = xml_dict.get('DisponibilidadHotelRespuesta')

                if response.get('coderr'):
                    return {'error': {'code': response.get('coderr'), 'text': response.get('txterr')}}

                hotels_data = response.get('infhot')
                if type(hotels_data) is dict:
                    hotels_data = [hotels_data]

                exclude_room_services_attrs = ['ROOM_COMMERCIALNAME', 'ROOM']

                hotels = []
                for hotel in hotels_data:
                    availability = {}
                    rooms_data = hotel.get('infhab', []) or []
                    for room in rooms_data:
                        if room.get('@id') and room.get('@refdis') and room.get('cupest') in ['DS']:
                            if room.get('@refdis') not in availability:
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
                                description=next(
                                    (obj for obj in (room.get('notser', []) or []) if obj.get('refnot') == 'ROOM'),
                                    {}
                                ).get('txtinf'),
                                commercial_name=next(
                                    (obj for obj in (room.get('notser', []) or []) if
                                     obj.get('refnot') == 'ROOM_COMMERCIALNAME'),
                                    {}
                                ).get('txtinf'),
                                services=[RoomService(
                                    reference=service.get('refnot'),
                                    name=service.get('txtinf')
                                ) for service in (room.get('notser', []) or []) if
                                    service.get('refnot') not in exclude_room_services_attrs],
                                cancellation_restrictions=cancellation_restrictions,
                                non_commissionable_amount=float(room.get('impnoc', '0') or '0'),
                                commissionable_amount=float(room.get('impcom', '0') or '0'),
                                fare_code=room.get('codtrf'),
                                fare_name=room.get('nomtrf'),
                            ))

                    hotels.append(Hotel(
                        reference=hotel.get('@id'),
                        name=hotel.get('nomser'),
                        category=hotel.get('codsca'),
                        services=hotel.get('codcas', []) or [],
                        code=hotel.get('codser'),
                        availability=availability,
                    ))

                return {'availability': hotels, 'session_id': self.TOKEN}

            except Exception as e:
                return {'error': {'code': 500, 'text': f'Unknown error. {e}'}}
        else:
            return {'error': {'code': 500, 'text': 'Unknown error'}}

    def block(self, hotel_id, distributions):
        customer_type_map = {'adults': 'adl', 'children': 'nin'}
        customers_data = {'adl': [], 'nin': []}
        rooms_data = []

        for room_id, dist in distributions.items():
            customers_id = []
            for customer in dist:
                customers_id += [customer.get('id')]

                customers_data[customer_type_map.get(customer.get('customer_type'))] += [
                    {
                        '@id': customer.get('id'),
                        'fecnac': customer.get('birthdate')
                    }
                ]

            rooms_data += [{
                '@id': room_id,
                'pasid': customers_id,
                'numuni': '1'
            }]

        json_data = {
            'BloqueoServicioPeticion': {
                'ideses': self.TOKEN,
                'codtou': 'HTI',
                'pasage': customers_data,
                'bloser': {
                    '@id': hotel_id,
                    'dissmo': rooms_data
                },
                'accion': 'A'
            }
        }

        xml_data = xmltodict.unparse(json_data, pretty=True, full_document=False)

        print('XML REQUEST', xml_data)

        response = requests.post(self.URI, data=xml_data, headers=self.HEADERS)

        if response and response.status_code == 200:
            try:
                print('XML RESPONSE', response.text)
                xml_dict = xmltodict.parse(response.text)
                response = xml_dict.get('BloqueoServicioRespuesta')

                if response.get('coderr'):
                    return {'error': {'code': response.get('coderr'), 'text': response.get('txterr')}}

                exclude_room_services_attrs = ['ROOM_COMMERCIALNAME', 'ROOM']

                passenger_data = {}
                for key, value in response.get('pasage', {}).items():
                    if type(value) is dict:
                        value = [value]
                    for item in value:
                        passenger_data[item.get('@id')] = {
                            'birth_date': item.get('fecnac'),
                            'non_commissionable_amount': item.get('impnoc'),
                            'commissionable_amount': item.get('impcom'),
                            'type': key[0].upper(),
                            'id': item.get('@id'),
                        }

                reserve_data = response.get('resser', {}).get('estsmo', [])
                if type(reserve_data) is dict:
                    reserve_data = [reserve_data]

                payment_info = response.get('infrsr', {}).get('infrpg', {})

                if type(payment_info) is dict:
                    payment_info = [payment_info]

                return {'response': {
                    'start_date': response.get('resser', {}).get('fecini'),
                    'end_date': response.get('resser', {}).get('fecfin'),
                    'hotel': {
                        'name': response.get('resser', {}).get('nomser'),
                        'category': response.get('resser', {}).get('codsca'),
                        'zone_code': response.get('resser', {}).get('codzge'),
                        'code': response.get('resser', {}).get('codser'),
                        'commissionable_amount': response.get('impnoc', 0),
                        'non_commissionable_amount': response.get('impcom', 0),
                    },
                    'payment': {
                        'currency': response.get('coddiv'),
                        'total_amount': sum([float(pay.get('inffpg', {}).get('imptot')) for pay in payment_info]),
                        'limit_date': min([pay.get('inffpg', {}).get('fecpag') for pay in payment_info]),
                    },
                    'rooms': [
                        {
                            'id': item['@id'],
                            'fare_code': item['codtrf'],
                            'fare_name': item['nomtrf'],
                            'room_type': item['codsmo'],
                            'cancellation_restrictions': {
                                'limit_date': item.get('rstcan', {}).get('feccan'),
                                'amount': item.get('rstcan', {}).get('impcan'),
                            },
                            'customers': [passenger_data[pax] for pax in item.get('estpas', {}).get('pasid', [])],
                            'commissionable_amount': item.get('impcom', 0),
                            'non_commissionable_amount': item.get('impnoc', 0),
                            'description': next(
                                (obj for obj in (item.get('notser', []) or []) if obj.get('refnot') == 'ROOM'),
                                {}
                            ).get('txtinf'),
                            'commercial_name': next(
                                (obj for obj in (item.get('notser', []) or []) if
                                 obj.get('refnot') == 'ROOM_COMMERCIALNAME'),
                                {}
                            ).get('txtinf'),
                            'services': [RoomService(
                                reference=service.get('refnot'),
                                name=service.get('txtinf')
                            ) for service in (item.get('notser', []) or []) if
                                service.get('refnot') not in exclude_room_services_attrs],
                        } for item in reserve_data
                    ]
                }, 'session_id': self.TOKEN}
            except Exception as e:
                print(f'Error: {e}')
        else:
            raise Exception(f'Error: {response}')

    def reserve(self, contact_information, customers, notes):
        notes_data = {}
        if notes:
            notes_data = {'notser': {'@id': 1, 'txtinf': notes}}
        json_data = {
            'ReservaCerrarPeticion': {
                'ideses': self.TOKEN,
                'codtou': 'HTI',
                'accion': 'F',
                **notes_data,
                'infpas': [
                    {
                        '@id': customer.get('id'),
                        'fecnac': format(customer.get('birthdate'), '%d/%m/%Y'),
                        'nombre': customer.get('first_name'),
                        'priape': customer.get('last_name'),
                    }
                    for customer in customers
                ],
                'percon': {
                    '@id': 1,
                    'nombre': contact_information.get('first_name'),
                    'priape': contact_information.get('last_name'),
                    'tel': contact_information.get('phone'),
                    'mai': contact_information.get('email'),
                    'pasapt': contact_information.get('document_number'),
                }
            }
        }

        xml_data = xmltodict.unparse(json_data, pretty=True, full_document=False)
        print('XML REQUEST', xml_data)
        response = requests.post(self.URI, data=xml_data, headers=self.HEADERS)
        if response and response.status_code == 200:
            try:
                print('XML RESPONSE', response.text)
                xml_dict = xmltodict.parse(response.text)
                response = xml_dict.get('ReservaCerrarRespuesta')

                if response.get('coderr'):
                    return {'error': {'code': response.get('coderr'), 'text': response.get('txterr')}}

                return {'response': self.as_reservation(response), 'session_id': self.TOKEN}
            except Exception as e:
                raise Exception(f'Error: {e}')
        else:
            raise Exception(f'Error: {response}')

    def as_reservation(self, response):
        passengers = response.get('respas', [])
        if type(passengers) is dict:
            passengers = [passengers]
        hotel = response.get('resser', {})
        rooms_data = hotel.get('estsmo', [])
        if type(rooms_data) is dict:
            rooms_data = [rooms_data]
        rooms = []

        for item in rooms_data:
            customers = item.get('estpas', {}).get('pasid', [])
            if type(customers) is dict:
                customers = [customers]
            rooms += [{
                'id': item.get('@id'),
                'type': item.get('codsmo'),
                'fare_code': item.get('codtrf'),
                'fare_name': item.get('nomtrf'),
                'status': item.get('cupest'),
                'commissionable_amount': item.get('impcom'),
                'non_commissionable_amount': item.get('impnoc'),
                'locator': item.get('locata'),
                'cancellation_restrictions': {
                    'date': item.get('rstcan', {}).get('feccan'),
                    'amount': item.get('rstcan', {}).get('impcan'),
                },
                'customers': customers
            }]

        return {
            'locator': response.get('locata'),
            'status': response.get('cupest'),
            'created_at': response.get('feccre'),
            'start_date': response.get('fecini'),
            'end_date': response.get('fecfin'),
            'currency': response.get('coddiv'),
            'commissionable_amount': response.get('impcom'),
            'non_commissionable_amount': response.get('impnoc'),
            'passengers': [
                {'id': item.get('@id'), 'birthdate': item.get('fecnac'), 'type': item.get('tippas'),
                 'commissionable_amount': item.get('impcom'),
                 'non_commissionable_amount': item.get('impnoc'), }
                for item in passengers
            ],
            'hotel': {
                'id': hotel.get('@id'),
                'start_date': hotel.get('fecini'),
                'end_date': hotel.get('fecfin'),
                'name': hotel.get('nomser'),
                'category': hotel.get('codsca'),
                'zone_code': hotel.get('codzge'),
                'hotel_code': hotel.get('codser'),
                'commissionable_amount': hotel.get('impcom'),
                'non_commissionable_amount': hotel.get('impnoc'),
            },
            'rooms': rooms,
            'contact_info': {
                'id': response.get('percon', {}).get('@id'),
                'first_name': response.get('percon', {}).get('nombre'),
                'last_name': response.get('percon', {}).get('priape'),
                'document_number': response.get('percon', {}).get('pasapt'),
                'phone': response.get('percon', {}).get('tel'),
                'email': response.get('percon', {}).get('mai'),
            },
            'notes': response.get('notser', {}).get('txtinf')
        }

    def list_reservations(self, first_name=None, last_name=None, document_number=None, start_date=None, end_date=None,
                          per_page=20, page=1):
        filters = {'numrst': per_page, 'indpag': page}
        if start_date:
            filters.update({'fecini': start_date})
        if end_date:
            filters.update({'fecfin': end_date})
        if first_name:
            filters.update({'nombre': first_name})
        if last_name:
            filters.update({'priape': last_name})
        if document_number:
            filters.update({'pasapt': document_number})

        json_data = {
            'ReservaListarPeticion': {
                'ideses': self.TOKEN,
                'codtou': 'HTT',
                **filters
            }
        }

        xml_data = xmltodict.unparse(json_data, pretty=True, full_document=False)
        response = requests.post(self.URI, data=xml_data, headers=self.HEADERS)

        if response and response.status_code == 200:
            try:
                xml_dict = xmltodict.parse(response.text)
                response = xml_dict.get('ReservaListarRespuesta')

                if response.get('coderr'):
                    return {'error': {'code': response.get('coderr'), 'text': response.get('txterr')}}

                reservations = [{
                    'locator': item.get('locata'),
                    'status': item.get('cupest'),
                    'hotel_code': item.get('codser'),
                    'created_at': item.get('timcre'),
                    'start_date': item.get('fecini'),
                    'end_date': item.get('fecfin'),
                    'currency': item.get('coddiv'),
                    'commissionable_amount': item.get('impcom'),
                    'non_commissionable_amount': item.get('impnoc'),
                    'name': item.get('percon', {}).get('nombre'),
                } for item in response.get('estres')]
                return {'response': reservations}
            except Exception as e:
                raise Exception(f'Error: {e}')
        else:
            raise Exception(f'Error: {response}')

    def get_reservation(self, locator):
        json_data = {
            'ReservaAbrirPeticion': {
                'ideses': self.TOKEN,
                'codtou': 'HTI',
                'locata': locator,
            }
        }

        xml_data = xmltodict.unparse(json_data, pretty=True, full_document=False)
        response = requests.post(self.URI, data=xml_data, headers=self.HEADERS)

        if response and response.status_code == 200:
            try:
                xml_dict = xmltodict.parse(response.text)
                response = xml_dict.get('ReservaAbrirRespuesta')

                if response.get('coderr'):
                    return {'error': {'code': response.get('coderr'), 'text': response.get('txterr')}}

                return {'response': self.as_reservation(response)}
            except Exception as e:
                raise Exception(f'Error: {e}')
        else:
            raise Exception(f'Error: {response}')

    def cancel_reservation(self, locator):
        json_data = {
            'ReservaCancelarPeticion': {
                'ideses': self.TOKEN,
                'codtou': 'HTT',
                'locata': locator,
            }
        }

        xml_data = xmltodict.unparse(json_data, pretty=True, full_document=False)
        response = requests.post(self.URI, data=xml_data, headers=self.HEADERS)

        if response and response.status_code == 200:
            try:
                xml_dict = xmltodict.parse(response.text)
                response = xml_dict.get('ReservaCancelarRespuesta')

                if response.get('coderr'):
                    return {'error': {'code': response.get('coderr'), 'text': response.get('txterr')}}

                return {'response': {
                    'currency': response.get('coddiv'),
                    'cancellation_amount': response.get('impcan'),
                    'locator': response.get('locata')}}
            except Exception as e:
                raise Exception(f'Error: {e}')
        else:
            raise Exception(f'Error: {response}')

    def get_hotels_information(self, zone_code: str):
        json_data = {
            'InformacionServicioPeticion': {
                'ideses': self.TOKEN,
                'codtou': 'HTI',
                'codzge': zone_code,
            }
        }
        xml_data = xmltodict.unparse(json_data, pretty=True, full_document=False)
        response = requests.post(self.URI, data=xml_data, headers=self.HEADERS)

        if response and response.status_code == 200:
            try:
                xml_dict = xmltodict.parse(response.text)
                response = xml_dict.get('InformacionServicioRespuesta')

                if response.get('coderr'):
                    return {'error': {'code': response.get('coderr'), 'text': response.get('txterr')}}

                return {'response': response.get('servic')}
            except Exception as e:
                raise Exception(f'Error: {e}')
        else:
            raise Exception(f'Error: {response}')

    def get_hotel_information(self, hotel_code: str):
        json_data = {
            'InformacionServicioPeticion': {
                'ideses': self.TOKEN,
                'codtou': 'HTI',
                'codser': hotel_code,
            }
        }
        xml_data = xmltodict.unparse(json_data, pretty=True, full_document=False)
        response = requests.post(self.URI, data=xml_data, headers=self.HEADERS)

        if response and response.status_code == 200:
            try:
                xml_dict = xmltodict.parse(response.text)
                response = xml_dict.get('InformacionServicioRespuesta')

                if response.get('coderr'):
                    return {'error': {'code': response.get('coderr'), 'text': response.get('txterr')}}

                return {'response': response.get('servic')}
            except Exception as e:
                raise Exception(f'Error: {e}')
        else:
            raise Exception(f'Error: {response}')
