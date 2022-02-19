from claim import ClaimItemSubmit, ClaimServiceSubmit
from claim.models import Claim, ClaimItem, ClaimService
import base64
import hashlib
import re

from claim import ClaimItemSubmit, ClaimServiceSubmit, ClaimConfig
from claim.models import Claim, ClaimItem, ClaimService, ClaimAttachment
from location.models import HealthFacility
from medical.models import Diagnosis, Item, Service
from insuree.models import InsureePolicy
from policy.models import Policy
from django.utils.translation import gettext
import core
from sosys.models import Employer
from sosys.models import SubProduct
from api_fhir_r4.configurations import R4IdentifierConfig, R4ClaimConfig
from api_fhir_r4.converters import BaseFHIRConverter, LocationConverter, PatientConverter, PractitionerConverter, \
    ReferenceConverterMixin, PractitionerRoleConverter
from api_fhir_r4.converters.conditionConverter import ConditionConverter
from api_fhir_r4.converters.medicationConverter import MedicationConverter
from api_fhir_r4.converters.healthcareServiceConverter import HealthcareServiceConverter
from api_fhir_r4.converters.activityDefinitionConverter import ActivityDefinitionConverter
from api_fhir_r4.converters.coverageConverter import CoverageConverter
from api_fhir_r4.models import Claim as FHIRClaim, ClaimItem as FHIRClaimItem, Period, ClaimDiagnosis, Money, \
    ImisClaimIcdTypes, ClaimSupportingInfo, Quantity, Condition, Extension, Reference, CodeableConcept, ClaimInsurance, \
    Attachment
from api_fhir_r4.utils import TimeUtils, FhirUtils, DbManagerUtils
from api_fhir_r4.exceptions import FHIRRequestProcessException

from api_fhir.configurations import Stu3IdentifierConfig, Stu3ClaimConfig
import datetime
from django.db import connection

from product import models as product_models
class ClaimConverter(BaseFHIRConverter, ReferenceConverterMixin):
    claim_uuid=""
    isReclaim = False
    
    STATUS_REJECTED = 1
    STATUS_ENTERED = 2
    STATUS_CHECKED = 4
    STATUS_PROCESSED = 8
    STATUS_RECOMMENDED = 6
    STATUS_FORWARDED = 9
    STATUS_VALUATED = 16
    @classmethod
    def to_fhir_obj(cls, imis_claim):
        fhir_claim = FHIRClaim()
        fhir_claim.extension = []
        fhir_claim.extension.append(cls.getSchemeInformation(imis_claim.product_id,imis_claim.subProduct_id))
        #fhir_claim.extension.append(cls.getSubProductInformation(imis_claim.subProduct_id))
        claim_uuid= imis_claim.uuid
        cls.build_fhir_pk(fhir_claim, imis_claim.uuid)
        fhir_claim.created = imis_claim.date_claimed.isoformat()
        fhir_claim.facility = HealthcareServiceConverter.build_fhir_resource_reference(imis_claim.health_facility,imis_claim.health_facility.code)
        cls.build_fhir_identifiers(fhir_claim, imis_claim)
        fhir_claim.patient = PatientConverter.build_fhir_resource_reference(imis_claim.insuree, imis_claim.insuree.chf_id)
        cls.build_fhir_billable_period(fhir_claim, imis_claim)
        cls.build_fhir_diagnoses(fhir_claim, imis_claim)
        cls.build_fhir_total(fhir_claim, imis_claim)
        if imis_claim.admin is not None:
            fhir_claim.enterer = PractitionerConverter.build_fhir_resource_reference(imis_claim.admin, 'Practitioner')
        else:
            raise FHIRRequestProcessException(
                [F'Failed to create FHIR instance for claim {imis_claim.uuid}: Claim Admin field not found'])
        cls.build_fhir_type(fhir_claim, imis_claim)
        cls.build_fhir_supportingInfo(fhir_claim, imis_claim)
        cls.build_fhir_items(fhir_claim, imis_claim)
        cls.build_fhir_provider(fhir_claim, imis_claim)
        cls.build_fhir_use(fhir_claim)
        cls.build_fhir_priority(fhir_claim)
        cls.build_fhir_status(fhir_claim,imis_claim)
        cls.build_fhir_payment_status(fhir_claim,imis_claim)
        cls.build_fhir_insurance(fhir_claim, imis_claim)
        cls.build_fhir_attachments(fhir_claim, imis_claim)
        cls.build_fhir_accident(fhir_claim, imis_claim)
        return fhir_claim
    @classmethod
    def to_imis_obj(cls, fhir_claim, audit_user_id):
        errors = []
        imis_claim = Claim()
        print("check check")
        cls.build_imis_date_claimed(imis_claim, fhir_claim, errors)
        cls.build_imis_accident_data(imis_claim, fhir_claim, errors)
        cls.build_imis_health_facility(errors, fhir_claim, imis_claim)
        #cls.build_imis_identifier(imis_claim, fhir_claim, errors)
        cls.build_imis_patient(imis_claim, fhir_claim, errors)
        cls.build_imis_schema_identifier(imis_claim, fhir_claim, errors)
        cls.build_imis_subproduct_identifier(imis_claim, fhir_claim, errors)
        cls.build_imis_date_range(imis_claim, fhir_claim, errors)
        cls.build_imis_diagnoses(imis_claim, fhir_claim, errors)
        cls.build_imis_total_claimed(imis_claim, fhir_claim, errors)
        cls.build_imis_claim_admin(imis_claim, fhir_claim, errors)
        cls.build_imis_visit_type(imis_claim, fhir_claim)
        cls.build_imis_supportingInfo(imis_claim, fhir_claim)
        cls.build_imis_submit_items_and_services(imis_claim, fhir_claim)
        cls.build_imis_attachments(imis_claim, fhir_claim)
        # cls.build_imis_adjuster(imis_claim, fhir_claim, errors)
        cls.check_errors(errors)
        return imis_claim

    def insertAccidentExtension(cls,urlValue,valueString,fhir_claim):
        if valueString:
            extension = Extension()
            extension.url = urlValue
            extension.valueString= valueString
            fhir_claim.extension.append(extension)
            
    @classmethod
    def build_fhir_accident(cls, fhir_claim, imis_claim):
        if imis_claim.employer:
            cls.insertAccidentExtension(cls,"Employer",imis_claim.employer.EmployerNameEng,fhir_claim)
            cls.insertAccidentExtension(cls,"EmployerID",imis_claim.employer.E_SSID,fhir_claim)
        cls.insertAccidentExtension(cls,"Admitted",imis_claim.is_admitted,fhir_claim)
        cls.insertAccidentExtension(cls,"WoundCondition",imis_claim.condition_of_wound,fhir_claim)
        cls.insertAccidentExtension(cls,"InjuredBodyPart",imis_claim.injured_body_part,fhir_claim)
        cls.insertAccidentExtension(cls,"IsDisable",imis_claim.is_disable,fhir_claim)
        cls.insertAccidentExtension(cls,"IsDead",imis_claim.is_dead,fhir_claim)
        cls.insertAccidentExtension(cls,"AccidentDescription",imis_claim.accident_description,fhir_claim)
        cls.insertAccidentExtension(cls,"ReasonOfSickness",imis_claim.reason_of_sickness,fhir_claim)
        cls.insertAccidentExtension(cls,"DischargeType",imis_claim.discharge_type,fhir_claim)
        cls.insertAccidentExtension(cls,"DischargeSummary",imis_claim.discharge_summary,fhir_claim)
        cls.insertAccidentExtension(cls,"DischargeDate",imis_claim.refer_to_date,fhir_claim)
        cls.insertAccidentExtension(cls,"Cancer",imis_claim.cancer,fhir_claim)
        cls.insertAccidentExtension(cls,"HIV",imis_claim.hiv,fhir_claim)
        cls.insertAccidentExtension(cls,"HeartAttack",imis_claim.heart_attack,fhir_claim)
        cls.insertAccidentExtension(cls,"HighBp",imis_claim.high_bp,fhir_claim)
        cls.insertAccidentExtension(cls,"Diabetes",imis_claim.diabetes,fhir_claim)
       
    def getSchemeInformation(schid, subid):
        sorex =  list(product_models.Product.objects.filter(id = schid))
        extension = Extension()
        extension.url = "scheme"
        if len(sorex) > 0:
            extension.valueString = sorex[0].name
        else:
            extension.valueString = "None"
        return extension
    
    
    def getSubProductInformation(schid):
        print(schid)
        sorex =  list(SubProduct.objects.filter(id = schid))
        extension = Extension()
        extension.url = "subProduct"
        if len(sorex) > 0:
            extension.valueString = sorex[0].sch_name_eng
        else:
            extension.valueString = "None"
        return extension
    @classmethod
    def get_reference_obj_id(cls, imis_claim):
        return imis_claim.uuid

    @classmethod
    def get_fhir_resource_type(cls):
        return FHIRClaim

    @classmethod
    def get_imis_obj_by_fhir_reference(cls, reference, errors=None):
        imis_claim_code = cls.get_resource_id_from_reference(reference)
        return DbManagerUtils.get_object_or_none(Claim, code=imis_claim_code)

    @classmethod
    def build_imis_date_claimed(cls, imis_claim, fhir_claim, errors):
        if fhir_claim.created:
            imis_claim.date_claimed = TimeUtils.str_to_date(fhir_claim.created)
        cls.valid_condition(imis_claim.date_claimed is None, gettext('Missing the date of creation'), errors)

    @classmethod
    def build_fhir_identifiers(cls, fhir_claim, imis_claim):
        identifiers = []
        cls.build_fhir_uuid_identifier(identifiers, imis_claim)
        claim_code = cls.build_fhir_identifier(imis_claim.code,
                                               R4IdentifierConfig.get_fhir_identifier_type_system(),
                                               R4IdentifierConfig.get_fhir_claim_code_type())
        identifiers.append(claim_code)
        fhir_claim.identifier = identifiers

    # @classmethod
    # def build_imis_identifier(cls, imis_claim, fhir_claim, errors):
    #     value = cls.get_fhir_identifier_by_code(fhir_claim.identifier, R4IdentifierConfig.get_fhir_claim_code_type())
    #     if value:
    #         imis_claim.code = value
    #     cls.valid_condition(imis_claim.code is None, gettext('Missing the claim code'), errors)

    @classmethod
    def build_imis_accident_data(cls, imis_claim, fhir_claim, errors):
        value = None
        if fhir_claim.extension:
            for x in fhir_claim.extension:
                if x.url == "IsReclaim":
                    value = x.valueString
                    cls.isReclaim= True
                    imis_claim.is_reclaim =value
                if x.url == "PreviousClaimCode" and cls.isReclaim == True:
                    value=x.valueString
                    codeValue='C'
                    if value[-1:] == 'C':
                        codeValue='R'
                    elif value[-1:] == 'R':
                        codeValue='S'
                    elif value[-1:] == 'S':
                        codeValue='T'
                    elif value[-1:] == 'T':
                        cls.valid_condition(True, gettext('Maximum reclaim reached!!!'), errors)
                    else:
                        cls.valid_condition(True, gettext('Invalid Claim Code'), errors)
                    imis_claim.code= str(value[:22]) + codeValue
                    imis_claim.explanation="Reclaim of "+ str(value)
                if x.url == "Admitted":
                    value = x.valueString
                    imis_claim.is_admitted =value
                if x.url == "WoundCondition":
                    value= x.valueString
                    imis_claim.condition_of_wound =value
                if x.url == "InjuredBodyPart":
                    value= x.valueString
                    imis_claim.injured_body_part =value
                if x.url == "IsDisable":
                    value=x.valueString
                    imis_claim.is_disable =value
                if x.url == "IsDead":
                    value=x.valueString
                    imis_claim.is_dead =value
                if x.url == "AccidentDescription":
                    value=x.valueString
                    imis_claim.accident_description =value
                if x.url == "ReasonOfSickness":
                    value=x.valueString
                    imis_claim.reason_of_sickness =value
                # if x.url == "family_disease":
                #     value=x.valueString
                #     imis_claim.is_admitted =value
                if x.url == "DischargeDate":
                    value=x.valueString
                    imis_claim.refer_to_date =value
                if x.url == "DischargeType":
                    value=x.valueString
                    imis_claim.discharge_type =value
                if x.url == "DischargeSummary":
                    value=x.valueString
                    imis_claim.discharge_summary =value
                if x.url == "Cancer":
                    value=x.valueString
                    imis_claim.cancer =value
                if x.url == "HIV":
                    value=x.valueString
                    imis_claim.hiv =value
                if x.url == "HeartAttack":
                    value=x.valueString
                    imis_claim.heart_attack =value
                if x.url == "HighBp":
                    value=x.valueString
                    imis_claim.high_bp =value
                if x.url == "Diabetes":
                    value=x.valueString
                    imis_claim.diabetes =value
                if x.url == "EmployerId":
                    value=x.valueString
                    obj = Employer.objects.get(E_SSID=value)
                    imis_claim.employer =obj
        # value = cls.get_fhir_identifier_by_code(fhir_claim.identifier, Stu3IdentifierConfig.get_fhir_schema_code_type())
        # if value:
        #     imis_claim.scheme_type = value
        # cls.valid_condition(imis_claim.scheme_type is None, gettext('Missing the Schema code'), errors)
    
    @classmethod
    def build_imis_schema_identifier(cls, imis_claim, fhir_claim, errors):
        value = None
        if fhir_claim.extension:
            for x in fhir_claim.extension:
                if x.url == "schemeType":
                    value = x.valueString
        # value = cls.get_fhir_identifier_by_code(fhir_claim.identifier, Stu3IdentifierConfig.get_fhir_schema_code_type())
        if value:
            imis_claim.scheme_type = value
        cls.valid_condition(imis_claim.scheme_type is None, gettext('Missing the Schema code'), errors)
    
    @classmethod
    def build_imis_subproduct_identifier(cls, imis_claim, fhir_claim, errors):
        value = None
        if fhir_claim.extension:
            for x in fhir_claim.extension:
                if x.url == "subProduct":
                    value = x.valueString
        # value = cls.get_fhir_identifier_by_code(fhir_claim.identifier, Stu3IdentifierConfig.get_fhir_schema_code_type())
        if value:
            imis_claim.subProduct = SubProduct.objects.get(id = value)
        cls.valid_condition(imis_claim.subProduct.id is None, gettext('Missing the Sub Product'), errors)

    @classmethod
    def build_imis_identifier(cls, imis_claim, fhir_claim, errors):
        value = cls.get_fhir_identifier_by_code(fhir_claim.identifier, R4IdentifierConfig.get_fhir_claim_code_type())
        if value:
            imis_claim.code = cls.generateCode(value)
        cls.valid_condition(imis_claim.code is None, gettext('Missing the claim code'), errors)

    def generateCode(claimCodeInitials):
        code= None
        sql = """\
                DECLARE @return_value int;
                EXEC @return_value = [dbo].[uspClaimSequenceNo] @oldclaimCode=null, @claimcodeinitials = '""" +claimCodeInitials +"""' ;      
                SELECT	'Return Value' = @return_value; 
            """
        with connection.cursor() as cur:
            try:
                cur.execute(sql)
                result_set = cur.fetchone()[0]
                code = claimCodeInitials + str("{:07d}".format(result_set))+"01C"
            finally:
                cur.close()
        return code


    @classmethod
    def build_imis_patient(cls, imis_claim, fhir_claim, errors):
        if fhir_claim.patient:
            insuree = PatientConverter.get_imis_obj_by_fhir_reference(fhir_claim.patient)
            if insuree:
                imis_claim.insuree = insuree
                imis_claim.insuree_chf_code = insuree.chf_id
        cls.valid_condition(imis_claim.insuree is None, gettext('Missing the patient reference'), errors)

    @classmethod
    def build_imis_health_facility(cls, errors, fhir_claim, imis_claim):
        if fhir_claim.facility:
            _, hfId = fhir_claim.facility.reference.split("/")
            health_facility =HealthFacility.objects.all() # DbManagerUtils.get_object_or_none(HealthFacility, uuid=hfId)
            if health_facility:
                imis_claim.health_facility = health_facility[0]
                imis_claim.health_facility_code = health_facility[0].code
                if cls.isReclaim == False:
                    currentYear = datetime.datetime.now()
                    code_value= "I"+str(health_facility[0].code)+str(currentYear.year)[1:]
                    claim_code= cls.generateCode(code_value)
                    imis_claim.code = claim_code
        cls.valid_condition(imis_claim.health_facility is None, gettext('Missing the facility reference'), errors)

    @classmethod
    def build_fhir_billable_period(cls, fhir_claim, imis_claim):
        billable_period = Period()
        try:
            if imis_claim.date_from:
                billable_period.start = imis_claim.date_from.isoformat()
            if imis_claim.date_to:
                billable_period.end = imis_claim.date_to.isoformat()
        except:
            billable_period = None
        fhir_claim.billablePeriod = billable_period

    @classmethod
    def build_imis_date_range(cls, imis_claim, fhir_claim, errors):
        billable_period = fhir_claim.billablePeriod
        if billable_period:
            if billable_period.start:
                imis_claim.date_from = TimeUtils.str_to_date(billable_period.start)
            if billable_period.end:
                imis_claim.date_to = TimeUtils.str_to_date(billable_period.end)
        cls.valid_condition(imis_claim.date_from is None, gettext('Missing the billable start date'), errors)
    
    
    """
    @classmethod
    def build_fhir_diagnoses(cls, fhir_claim, imis_claim):
        diagnoses = []
        cls.build_fhir_diagnosis(diagnoses, imis_claim.icd.code, ImisClaimIcdTypes.ICD_0.value)
        if imis_claim.icd_1:
            cls.build_fhir_diagnosis(diagnoses, imis_claim.icd_1, ImisClaimIcdTypes.ICD_1.value)
        if imis_claim.icd_2:
            cls.build_fhir_diagnosis(diagnoses, imis_claim.icd_2, ImisClaimIcdTypes.ICD_2.value)
        if imis_claim.icd_3:
            cls.build_fhir_diagnosis(diagnoses, imis_claim.icd_3, ImisClaimIcdTypes.ICD_3.value)
        if imis_claim.icd_4:
            cls.build_fhir_diagnosis(diagnoses, imis_claim.icd_4, ImisClaimIcdTypes.ICD_4.value)
        fhir_claim.diagnosis = diagnoses
    
    @classmethod
    def build_fhir_diagnosis(cls, diagnoses, icd_code, icd_type):
        claim_diagnosis = ClaimDiagnosis()
        claim_diagnosis.sequence = FhirUtils.get_next_array_sequential_id(diagnoses)
        #claim_diagnosis.diagnosisCodeableConcept = cls.build_codeable_concept(icd_code, None)
        fhir_condition = Condition()
        imis_claim = Claim()

        claim_diagnosis.diagnosisReference = ConditionConverter.build_fhir_resource_reference(imis_claim.code)
        claim_diagnosis.type = [cls.build_simple_codeable_concept(icd_type)]
        diagnoses.append(claim_diagnosis)
    """

    @classmethod
    def build_fhir_diagnoses(cls, fhir_claim, imis_claim):
        diagnoses = []
        cls.build_fhir_diagnosis(diagnoses, imis_claim.icd, ImisClaimIcdTypes.ICD_0.value)
        if imis_claim.icd_1 is not None:
            cls.build_fhir_diagnosis(diagnoses, imis_claim.icd_1, ImisClaimIcdTypes.ICD_1.value)
        if imis_claim.icd_2 is not None:
            cls.build_fhir_diagnosis(diagnoses, imis_claim.icd_2, ImisClaimIcdTypes.ICD_2.value)
        if imis_claim.icd_3 is not None:
            cls.build_fhir_diagnosis(diagnoses, imis_claim.icd_3, ImisClaimIcdTypes.ICD_3.value)
        if imis_claim.icd_4 is not None:
            cls.build_fhir_diagnosis(diagnoses, imis_claim.icd_4, ImisClaimIcdTypes.ICD_4.value)

        fhir_claim.diagnosis = diagnoses

    @classmethod
    def build_fhir_diagnosis(cls, diagnoses, icd_code, icd_type):
        if icd_code is None:
            raise FHIRRequestProcessException(['ICD code cannot be null'])
        if icd_type is None:
            raise FHIRRequestProcessException(['ICD Type cannot be null'])
        claim_diagnosis = ClaimDiagnosis()
        claim_diagnosis.sequence = FhirUtils.get_next_array_sequential_id(diagnoses)
        claim_diagnosis.diagnosisReference = ConditionConverter.build_fhir_resource_reference(icd_code)
        claim_diagnosis.type = [cls.build_codeable_concept(icd_type)]
        claim_diagnosis.name = cls.build_simple_codeable_concept(icd_code.name)
        diagnoses.append(claim_diagnosis)

    # TODO: fix the issue with POST
    @classmethod
    def build_imis_diagnoses(cls, imis_claim, fhir_claim, errors):
        diagnoses = fhir_claim.diagnosis
        if diagnoses:
            for diagnosis in diagnoses:
                diagnosis_type = cls.get_diagnosis_type(diagnosis)
                diagnosis_code = cls.get_diagnosis_code(diagnosis)
                if diagnosis_type == ImisClaimIcdTypes.ICD_0.value:
                    imis_claim.icd = cls.get_claim_diagnosis_by_code(diagnosis_code)
                    imis_claim.icd_code = diagnosis_code
                elif diagnosis_type == ImisClaimIcdTypes.ICD_1.value:
                    imis_claim.icd_1 = diagnosis_code
                    imis_claim.icd1_code = cls.get_claim_diagnosis_code_by_id(diagnosis_code)
                elif diagnosis_type == ImisClaimIcdTypes.ICD_2.value:
                    imis_claim.icd_2 = diagnosis_code
                    imis_claim.icd2_code = cls.get_claim_diagnosis_code_by_id(diagnosis_code)
                elif diagnosis_type == ImisClaimIcdTypes.ICD_3.value:
                    imis_claim.icd_3 = diagnosis_code
                    imis_claim.icd3_code = cls.get_claim_diagnosis_code_by_id(diagnosis_code)
                elif diagnosis_type == ImisClaimIcdTypes.ICD_4.value:
                    imis_claim.icd_4 = diagnosis_code
                    imis_claim.icd4_code = cls.get_claim_diagnosis_code_by_id(diagnosis_code)
        cls.valid_condition(imis_claim.icd is None, gettext('Missing the main diagnosis for claim'), errors)

    @classmethod
    def get_diagnosis_type(cls, diagnosis):
        diagnosis_type = None
        type_concept = cls.get_first_diagnosis_type(diagnosis)
        if type_concept:
            diagnosis_type = type_concept.text
        return diagnosis_type

    @classmethod
    def get_first_diagnosis_type(cls, diagnosis):
        return diagnosis.type[0]

    @classmethod
    def get_claim_diagnosis_by_code(cls, icd_code):
        return Diagnosis.objects.get(code=icd_code)

    @classmethod
    def get_claim_diagnosis_code_by_id(cls, diagnosis_id):
        code = None
        if diagnosis_id is not None:
            diagnosis = DbManagerUtils.get_object_or_none(Diagnosis, pk=diagnosis_id)
            if diagnosis:
                code = diagnosis.code
        return code

    @classmethod
    def get_diagnosis_code(cls, diagnosis):
        code = None
        concept = diagnosis.diagnosisCodeableConcept
        if concept:
            coding = cls.get_first_coding_from_codeable_concept(concept)
            icd_code = coding.code
            if icd_code:
                code = icd_code

        #if diagnosis.diagnosisReference:
            #code = ConditionConverter.get_imis_obj_by_fhir_reference(diagnosis.diagnosisReference)
            #if code:
            #    imis_claim.icd = code
            #    imis_claim.icd_code = code.code

        return code

    @classmethod
    def build_fhir_total(cls, fhir_claim, imis_claim):
        total_claimed = imis_claim.claimed
        if not total_claimed:
            total_claimed = 0
        fhir_total = Money()
        fhir_total.value = total_claimed
        # if hasattr(core, 'currency'):
            # fhir_total.currency = core.currency
        fhir_total.currency = "NRS"
        fhir_claim.total = fhir_total

    @classmethod
    def build_imis_total_claimed(cls, imis_claim, fhir_claim, errors):
        total_money = fhir_claim.total
        if total_money is not None:
            imis_claim.claimed = total_money.value
        cls.valid_condition(imis_claim.claimed is None,
                            gettext('Missing the value for `total` attribute'), errors)

    @classmethod
    def build_imis_claim_admin(cls, imis_claim, fhir_claim, errors):
        if fhir_claim.enterer:
            admin = PractitionerConverter.get_imis_obj_by_fhir_reference(fhir_claim.enterer)
            if admin:
                imis_claim.admin = admin
                imis_claim.claim_admin_code = admin.code
        cls.valid_condition(imis_claim.admin is None, gettext('Missing the enterer reference'), errors)

    @classmethod
    def build_fhir_type(cls, fhir_claim, imis_claim):
        if imis_claim.visit_type:
            fhir_claim.type = cls.build_simple_codeable_concept(imis_claim.visit_type)

    @classmethod
    def build_imis_visit_type(cls, imis_claim, fhir_claim):
        if fhir_claim.type:
            imis_claim.visit_type = fhir_claim.type.text

    @classmethod
    def build_fhir_supportingInfo(cls, fhir_claim, imis_claim):
        guarantee_id_code = R4ClaimConfig.get_fhir_claim_information_guarantee_id_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, guarantee_id_code, imis_claim.guarantee_id)
        explanation_code = R4ClaimConfig.get_fhir_claim_information_explanation_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, explanation_code, imis_claim.explanation)
        is_admitted = R4ClaimConfig.get_fhir_claim_information_is_admitted_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, is_admitted, imis_claim.is_admitted)
        accident_description = R4ClaimConfig.get_fhir_claim_information_accident_description_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, accident_description, imis_claim.accident_description)
        injured_body_part = R4ClaimConfig.get_fhir_claim_information_injured_body_part_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, injured_body_part, imis_claim.injured_body_part)
        discharge_type = R4ClaimConfig.get_fhir_claim_information_discharge_type_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, discharge_type, imis_claim.discharge_type)

        discharge_date = R4ClaimConfig.get_fhir_claim_information_discharge_date_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, discharge_date, imis_claim.refer_to_date)

        discharge_summary = R4ClaimConfig.get_fhir_claim_information_discharge_summary_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, discharge_summary, imis_claim.discharge_summary)

        condition_of_wound = R4ClaimConfig.get_fhir_claim_information_condition_of_wound_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, condition_of_wound, imis_claim.condition_of_wound)

        cancer = R4ClaimConfig.get_fhir_claim_information_cancer_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, cancer, imis_claim.cancer)

        heart_attack = R4ClaimConfig.get_fhir_claim_information_heart_attack_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, heart_attack, imis_claim.heart_attack)

        hiv = R4ClaimConfig.get_fhir_claim_information_hiv_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, hiv, imis_claim.hiv)

        high_bp = R4ClaimConfig.get_fhir_claim_information_high_bp_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, high_bp, imis_claim.high_bp)

        diabetes = R4ClaimConfig.get_fhir_claim_information_diabetes_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, diabetes, imis_claim.diabetes)

        reason_of_sickness = R4ClaimConfig.get_fhir_claim_information_reason_of_sickness_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, reason_of_sickness, imis_claim.reason_of_sickness)

        if imis_claim.refer_to_health_facility is not None:
            refer_to_health_facility = R4ClaimConfig.get_fhir_claim_information_refer_to_health_facility_code()
            cls.build_fhir_string_information(fhir_claim.supportingInfo, refer_to_health_facility, imis_claim.refer_to_health_facility.code)

        if imis_claim.refer_from_health_facility is not None:
            refer_from_health_facility = R4ClaimConfig.get_fhir_claim_information_refer_from_health_facility_code()
            cls.build_fhir_string_information(fhir_claim.supportingInfo, refer_from_health_facility,
                                              imis_claim.refer_from_health_facility.code)

        refer_from_date = R4ClaimConfig.get_fhir_claim_information_refer_from_date_code()
        cls.build_fhir_string_information(fhir_claim.supportingInfo, refer_from_date,
                                          imis_claim.refer_from_date)

    @classmethod
    def build_imis_supportingInfo(cls, imis_claim, fhir_claim):
        if fhir_claim.supportingInfo:
            for supportingInfo in fhir_claim.supportingInfo:
                category = supportingInfo.category
                if category and category.text == R4ClaimConfig.get_fhir_claim_information_guarantee_id_code():
                    imis_claim.guarantee_id = supportingInfo.valueString
                elif category and category.text == R4ClaimConfig.get_fhir_claim_information_explanation_code():
                    imis_claim.explanation = supportingInfo.valueString

    @classmethod
    def build_fhir_string_information(cls, claim_information, code, value_string):
        result = None
        if value_string:
            supportingInfo_concept = ClaimSupportingInfo()
            supportingInfo_concept.sequence = FhirUtils.get_next_array_sequential_id(claim_information)
            supportingInfo_concept.category = cls.build_simple_codeable_concept(code)
            supportingInfo_concept.valueString = value_string
            claim_information.append(supportingInfo_concept)
            result = supportingInfo_concept
        return result

    @classmethod
    def build_fhir_items(cls, fhir_claim, imis_claim):
        cls.build_items_for_imis_item(fhir_claim, imis_claim)
        cls.build_items_for_imis_services(fhir_claim, imis_claim)

    @classmethod
    def build_items_for_imis_item(cls, fhir_claim, imis_claim):
        for item in imis_claim.items.all():
            if item:
                type = R4ClaimConfig.get_fhir_claim_item_code()
                cls.build_fhir_item(fhir_claim, item.item.code, type, item)

    @classmethod
    def get_imis_items_for_claim(cls, imis_claim):
        items = []
        if imis_claim and imis_claim.id:
            items = ClaimItem.objects.filter(claim_id=imis_claim.id)
        return items

    @classmethod
    def build_fhir_item(cls, fhir_claim, code, item_type, item):
        fhir_item = FHIRClaimItem()
        fhir_item.sequence = FhirUtils.get_next_array_sequential_id(fhir_claim.item)
        unit_price = Money()
        unit_price.value = item.price_asked
        # if hasattr(core, 'currency'):
        #     unit_price.currency = core.currency
        unit_price.currency = "NRS"
        fhir_item.unitPrice = unit_price
        fhir_quantity = Quantity()
        fhir_quantity.value = item.qty_provided
        fhir_item.quantity = fhir_quantity
        fhir_item.productOrService = cls.build_simple_codeable_concept(code)
        fhir_item.category = cls.build_simple_codeable_concept(item_type)
        item_explanation_code = R4ClaimConfig.get_fhir_claim_item_explanation_code()
        fhir_item.name = cls.build_simple_codeable_concept(item.item.name if item_type == "item" else item.service.name)
        information = cls.build_fhir_string_information(fhir_claim.supportingInfo, item_explanation_code, item.explanation)
        if information:
            fhir_item.informationSequence = [information.sequence]

        extension = Extension()

        if fhir_item.category.text == "item":
            medication = cls.build_medication_extension(extension)
            fhir_item.extension.append(medication)

        elif fhir_item.category.text == "service":
            activity_definition = cls.build_activity_definition_extension(extension)
            fhir_item.extension.append(activity_definition)

        fhir_claim.item.append(fhir_item)

    @classmethod
    def build_items_for_imis_services(cls, fhir_claim, imis_claim):
        for service in imis_claim.services.all():
            if service:
                type = R4ClaimConfig.get_fhir_claim_service_code()
                cls.build_fhir_item(fhir_claim, service.service.code, type, service)

    @classmethod
    def get_imis_services_for_claim(cls, imis_claim):
        services = []
        if imis_claim and imis_claim.id:
            services = ClaimService.objects.filter(claim_id=imis_claim.id)
        return services

    @classmethod
    def build_medication_extension(cls, extension):
        #extension = Extension()
        imis_item = ClaimItem()
        reference = Reference()
        extension.valueReference = reference
        extension.url = "Medication"
        imis_item.item = Item()
        if imis_item.item is None:
            raise FHIRRequestProcessException(['Cannot construct medication on  None (Item) '] )
        extension.valueReference = MedicationConverter.build_fhir_resource_reference(imis_item.item)
        return extension

    @classmethod
    def build_activity_definition_extension(cls, extension):
        #extension = Extension()
        imis_service = ClaimService()
        reference = Reference()
        extension.valueReference = reference
        extension.url = "ActivityDefinition"
        imis_service.service = Service()
        if imis_service.service is None:
            raise FHIRRequestProcessException(['Cannot construct activity on None (service) '] )
        extension.valueReference = ActivityDefinitionConverter.build_fhir_resource_reference(imis_service.service)
        return extension

    @classmethod
    def build_imis_submit_items_and_services(cls, imis_claim, fhir_claim):
        imis_items = []
        imis_services = []
        if fhir_claim.item:
            for item in fhir_claim.item:
                if item.category:
                    if item.category.text == R4ClaimConfig.get_fhir_claim_item_code():
                        cls.build_imis_submit_item(imis_items, item)
                    elif item.category.text == R4ClaimConfig.get_fhir_claim_service_code():
                        cls.build_imis_submit_service(imis_services, item)
        # added additional attributes which will be used to create ClaimRequest in serializer
        imis_claim.submit_items = imis_items
        imis_claim.submit_services = imis_services

    @classmethod
    def build_imis_submit_item(cls, imis_items, fhir_item):
        price_asked = cls.get_fhir_item_price_asked(fhir_item)
        qty_provided = cls.get_fhir_item_qty_provided(fhir_item)
        item_code = cls.get_fhir_item_code(fhir_item)
        imis_items.append(ClaimItemSubmit(item_code, qty_provided, price_asked))

    @classmethod
    def build_imis_submit_service(cls, imis_services, fhir_item):
        price_asked = cls.get_fhir_item_price_asked(fhir_item)
        qty_provided = cls.get_fhir_item_qty_provided(fhir_item)
        service_code = cls.get_fhir_item_code(fhir_item)
        imis_services.append(ClaimServiceSubmit(service_code, qty_provided, price_asked))

    @classmethod
    def get_fhir_item_code(cls, fhir_item):
        item_code = None
        if fhir_item.productOrService:
            item_code = fhir_item.productOrService.text
        return item_code

    @classmethod
    def get_fhir_item_qty_provided(cls, fhir_item):
        qty_provided = None
        if fhir_item.quantity:
            qty_provided = fhir_item.quantity.value
        return qty_provided

    @classmethod
    def get_fhir_item_price_asked(cls, fhir_item):
        price_asked = None
        if fhir_item.unitPrice:
            price_asked = fhir_item.unitPrice.value
        return price_asked

    @classmethod
    def build_fhir_provider(cls, fhir_claim, imis_claim):
        #fhir_claim.provider = imis_claim.adjuster
        if imis_claim.admin is not None:
            fhir_claim.provider = PractitionerRoleConverter.build_fhir_resource_reference(imis_claim.admin)

    @classmethod
    def build_imis_adjuster(cls, imis_claim, fhir_claim, errors):
        adjuster = fhir_claim.provider
        if not cls.valid_condition(adjuster is None,
                                   gettext('Missing claim `adjuster` attribute'), errors):
            imis_claim.adjuster = adjuster

    @classmethod
    def build_fhir_use(cls, fhir_claim):
        fhir_claim.use = "claim"

    @classmethod
    def build_fhir_priority(cls, fhir_claim):
        fhir_claim.priority = cls.build_codeable_concept("normal", None, None)

    @classmethod
    def build_fhir_status(cls, fhir_claim,imis_claim):
        fhir_claim.status = cls.statusMapping(cls,imis_claim.status)

    PAYMENT_REJECTED=1
    PAYMENT_PROCESSING=0
    PAYMENT_COMPLETED=2
    @classmethod
    def build_fhir_payment_status(cls, fhir_claim,imis_claim):
        if cls.paymentMapping(cls,imis_claim.payment_status):
            fhir_claim.payment_status = cls.paymentMapping(cls,imis_claim.payment_status)#cls.statusMapping(cls,imis_claim.status)
    
    def paymentMapping(cls,payment_code):
        if payment_code==cls.PAYMENT_COMPLETED:
            return "Completed"
        if payment_code==cls.PAYMENT_PROCESSING:
            return "Processing"
        if payment_code==cls.PAYMENT_REJECTED:
            return "Rejected"
    def statusMapping(cls,status_code):
        if status_code == cls.STATUS_CHECKED:
            return "checked"
        elif status_code == cls.STATUS_ENTERED:
            return "entered"
        elif status_code == cls.STATUS_FORWARDED:
            return "forwarded"
        elif status_code == cls.STATUS_PROCESSED:
            return "processed"
        elif status_code == cls.STATUS_RECOMMENDED:
            return "recommended"
        elif status_code == cls.STATUS_REJECTED:
            return "rejected"
        elif status_code == cls.STATUS_VALUATED:
            return "valuated"
    @classmethod
    def build_fhir_insurance(cls, fhir_claim, imis_claim):
        fhir_insurance = ClaimInsurance()
        imis_insuree_policy  = imis_claim.insuree.insuree_policies.all()
        # fixme get latest policy, not the one active at the claim
        for pol in imis_insuree_policy:
            policy = pol.policy
            fhir_insurance.coverage = CoverageConverter.build_fhir_resource_reference(policy)

        if fhir_insurance.coverage is None:
            fhir_insurance.coverage = Reference()
            fhir_insurance.coverage.reference = "Coverage"
            
        fhir_insurance.sequence = 0
        fhir_insurance.focal = True

        fhir_claim.insurance = [fhir_insurance]

    @classmethod
    def build_imis_attachments(cls, imis_claim: Claim, fhir_claim: FHIRClaim):
        supporting_info = fhir_claim.supportingInfo
        if not hasattr(imis_claim, 'claim_attachments'):
            imis_claim.claim_attachments = []

        for next_attachment in supporting_info:
            if next_attachment.category.text == R4ClaimConfig.get_fhir_claim_attachment_code():
                claim_attachment = cls.build_attachment_from_value(next_attachment.valueAttachment)
                imis_claim.claim_attachments.append(claim_attachment)

    @classmethod
    def build_fhir_attachments(cls, fhir_claim, imis_claim):
        attachments = ClaimAttachment.objects.filter(claim=imis_claim)

        if not fhir_claim.supportingInfo:
            fhir_claim.supportingInfo = []

        for attachment in attachments:
            supporting_info_element = cls.build_attachment_supporting_info_element(attachment)
            fhir_claim.supportingInfo.append(supporting_info_element)

    @classmethod
    def build_attachment_supporting_info_element(cls, imis_attachment):
        supporting_info_element = ClaimSupportingInfo()

        supporting_info_element.category = cls.build_attachment_supporting_info_category()
        supporting_info_element.valueAttachment = cls.build_fhir_value_attachment(imis_attachment)
        return supporting_info_element

    @classmethod
    def build_attachment_supporting_info_category(cls):
        category_code = R4ClaimConfig.get_fhir_claim_attachment_code()
        system = R4ClaimConfig.get_fhir_claim_attachment_system()
        category = cls.build_codeable_concept(category_code, system, category_code)
        category.coding[0].display = category_code.capitalize()
        return category

    @classmethod
    def build_fhir_value_attachment(cls, imis_attachment):
        attachment = Attachment()
        try:
            attachment.creation = imis_attachment.date.isoformat()
        except:
            print("")
        attachment.data = cls.get_attachment_content(imis_attachment)
        attachment.contentType = imis_attachment.mime
        attachment.title = imis_attachment.filename
        return attachment

    @classmethod
    def get_attachment_content(cls, imis_attachment):
        file_root = ClaimConfig.claim_attachments_root_path

        if file_root and imis_attachment.url:
            with open('%s/%s' % (ClaimConfig.claim_attachments_root_path, imis_attachment.url), "rb") as file:
                return base64.b64encode(file.read())
        elif not imis_attachment.url and imis_attachment.document:
            return imis_attachment.document
        else:
            return None

    @classmethod
    def build_attachment_from_value(cls, valueAttachment: Attachment):
        allowed_mime_regex = R4ClaimConfig.get_allowed_fhir_claim_attachment_mime_types_regex()
        mime_validation = re.compile(allowed_mime_regex, re.IGNORECASE)

        if not mime_validation.match(valueAttachment.contentType):
            if valueAttachment.contentType != "application/pdf":
                raise ValueError(F'Mime type {valueAttachment.contentType} not allowed')

        if valueAttachment.hash:
            cls.validateHash(valueAttachment.hash, valueAttachment.data)

        attachment_data = {
            'title': valueAttachment.title,
            'filename': valueAttachment.title,
            'document': valueAttachment.data,
            'mime': valueAttachment.contentType,
            'date': TimeUtils.str_to_date(valueAttachment.creation)
        }
        return attachment_data

    @classmethod
    def validateHash(cls, expected_hash, data):
        actual_hash = hashlib.sha1(data.encode('utf-8')).hexdigest()
        if actual_hash.casefold() != expected_hash.casefold():
            raise ValueError('Hash for data file is incorrect')
