from django.utils.translation import gettext
from location.models import HealthFacility, Location, HealthFacilityCatchment
from  insuree.models import Insuree,Family,FamilyType,Gender,Photo,InsureePolicy
from api_fhir_r4.configurations import GeneralConfiguration, R4IdentifierConfig, R4LocationConfig
from api_fhir_r4.converters import  BaseFHIRConverter, ReferenceConverterMixin
from api_fhir_r4.models import EmployerService,EmployeeService
from api_fhir_r4.utils import TimeUtils, DbManagerUtils
from sosys.models import Employer
import json
# from django.contrib.sites.models import Site
from django.db import connection
class EmployeeeServiceConverter(BaseFHIRConverter, ReferenceConverterMixin):

    @classmethod
    def to_fhir_obj(cls, imis_emp):
        fhir_emp = EmployeeService ()
        cls.build_fhir_pk(fhir_emp, imis_emp.uuid)
        cls.build_fhir_employer_service_identifier(fhir_emp, imis_emp)
        cls.build_fhir_emp_name(fhir_emp, imis_emp)
        cls.build_fhir_company(fhir_emp,imis_emp)
        cls.build_fhir_CHFID(fhir_emp,imis_emp)
        cls.build_fhir_family(fhir_emp,imis_emp)
        return fhir_emp
    
    @classmethod
    def build_fhir_employer_service_identifier(cls, fhir_emp, imis_emp):
        identifiers = []
        cls.build_fhir_uuid_identifier(identifiers, imis_emp)
        # cls.build_fhir_hf_code_identifier(identifiers, imis_hf)
        fhir_emp.identifier = identifiers

    @classmethod
    def build_fhir_emp_name(cls, fhir_emp, imis_emp):
        fhir_emp.other_names = imis_emp.other_names
        fhir_emp.last_name = imis_emp.last_name

    @classmethod
    def build_fhir_CHFID(cls, fhir_emp, imis_emp):
        currentUUID = fhir_emp.identifier[0].value
        companyItem =[]        
        sql = """\
                select CHFID,FamilyID
                 from   [dbo].[tblInsuree]   where 
                InsureeUUID= '"""+str(currentUUID)+"""';
            """
        with connection.cursor() as cur:
            try:
                cur.execute(sql)
                result_set = cur.fetchall()
                # current_site = Site.objects.get_current()
                # site_domain =current_site.domain
                for data in result_set:
                    fhir_emp.CHFID=str(data[0])
                    fhir_emp.FamilyId=str(data[1])
                    # companyItem.append(empData)
            finally:
                cur.close()
    @classmethod
    def build_fhir_family(cls, fhir_emp, imis_emp):
        currentFID = fhir_emp.FamilyId
        currentUUID = fhir_emp.identifier[0].value
        familyItem =[]        
        sql = """\
                select InsureeID,FamilyID,Relationship,IsHead,OtherNames,LastName,CHFID from tblInsuree where FamilyID=  '"""+str(currentFID)+"""' and InsureeUUID != '""" +currentUUID+"""';
            """
        print(sql)
        with connection.cursor() as cur:
            try:
                cur.execute(sql)
                result_set = cur.fetchall()
                # current_site = Site.objects.get_current()
                # site_domain =current_site.domain
                for data in result_set:
                    famData= {  "name": str(data[4]) + " " + str(data[5]), "IsHead": str(data[3]), "CHFID":str(data[6])}
                    familyItem.append(famData)
            finally:
                cur.close()
        fhir_emp.Family.append(familyItem)
    @classmethod
    def build_fhir_company(cls, fhir_emp, imis_emp):
        currentUUID = fhir_emp.identifier[0].value
        companyItem =[]        
        sql = """\
                select semp.E_SSID, semp.EmployerNameEng,
                 semp.EmployerNameNep, semp.Status ,tbins.CHFID
                 from ([dbo].[sosys_insureeemployer] insemp 
                left join [dbo].[tblInsuree] tbins on 
                tbins.InsureeID = insemp.insuree_id)
                left join [dbo].[sosys_employer] semp 
                on semp.E_SSID = insemp.employer_id where 
                tbins.InsureeUUID= '"""+str(currentUUID)+"""';
            """
        with connection.cursor() as cur:
            try:
                cur.execute(sql)
                result_set = cur.fetchall()
                # current_site = Site.objects.get_current()
                # site_domain =current_site.domain
                for data in result_set:
                    empData= { "fullUrl": "/api_fhir_r4/Employee/"+str(data[0]),"E_SSID": str(data[0]), "name": str(data[1]), "status": str(data[3])}
                    # if fhir_emp.CHFID == None:
                    #     fhir_emp.CHFID=str(data[4])
                    companyItem.append(empData)
            finally:
                cur.close()
        fhir_emp.company.append(companyItem)


class EmployerServiceConverter(BaseFHIRConverter, ReferenceConverterMixin):

    @classmethod
    def to_fhir_obj(cls, imis_emp):
        fhir_emp =EmployerService()
        # cls.build_fhir_pk(fhir_emp, imis_emp.E_SSID)
        # cls.build_fhir_employee_service_identifier(fhir_emp, imis_emp)
        cls.build_fhir_emp_name(fhir_emp, imis_emp)
        return fhir_emp
    
    @classmethod
    def build_fhir_employee_service_identifier(cls, fhir_emp, imis_emp):
        identifiers = []
        cls.build_fhir_uuid_identifier(identifiers, imis_emp)
        # cls.build_fhir_hf_code_identifier(identifiers, imis_hf)
        fhir_emp.identifier = identifiers

    @classmethod
    def build_fhir_emp_name(cls, fhir_emp, imis_emp):
        fhir_emp.E_SSID = imis_emp.E_SSID
        fhir_emp.EmployerNameEng = imis_emp.EmployerNameEng
        fhir_emp.Status = imis_emp.Status