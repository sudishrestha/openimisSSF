from api_fhir_r4.models import Property, PropertyList,BackboneElement, DomainResource
from enum import Enum

class EmployeeService (DomainResource):
    identifier = Property('identifier', 'Identifier', count_max='*')
    other_names = Property('other_names', str)
    last_name = Property('last_name', str)
    E_SSID = Property('E_SSID', str)   
    CHFID = Property('CHFID', str)    
    FamilyId = Property('FamilyId', str)    
    Family = Property('Family', 'Reference', count_max='*')    
    company = Property('company', 'EmployerService', count_max='*')
class  EmployerService (DomainResource):
    model_prefix = "item"
    identifier = Property('identifier', 'Identifier', count_max='*')
    E_SSID = Property('E_SSID', str)
    EmployerNameEng = Property('EmployerNameEng', str)
    Status = Property('Status', str)
    # company = Property('company', 'Reference') 