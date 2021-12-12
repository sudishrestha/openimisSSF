from claim.models import Claim
from rest_framework import serializers
# from sosys.models import STB_ANUSUCHI2_COMPONENT
from location.models import HealthFacility
from medical.models import Item, Service, Diagnosis
from .models import (
    ClaimRecommend,
    Address,
    Dependent,
    Employer,
    Insuree,
    InsureeEmployer,
    Bank,
    BankBranch,
    ClaimDocumentsMaster
)

class EmployerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employer
        fields = '__all__'

class InsureeEmployerSerializer(serializers.ModelSerializer):
    employer = EmployerSerializer(many=False)
    class Meta:
        model = InsureeEmployer
        fields = '__all__'

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'
        # fields = ('AddressId','DistrictName','VDCName','Ward','ToleNameEng','ToleNameNep','HouseNumber','Status')

class DependentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dependent
        # fields = ('RelationType','p_ssid')
        fields = '__all__'
        # depth = 1

class InsureeSerializer(serializers.ModelSerializer):
    AddressId = AddressSerializer(many=False)
    dep_set = DependentSerializer(many=True)

    class Meta:
        model = Insuree
        # fields = ('p_ssid','dep_set','addresses')
        fields = '__all__'

    def to_representation(self, instance):
         # instance is the model object. create the custom json format by accessing instance attributes normaly and return it


        identifier = list()
        identifierObj = dict()
        
        xyz =list()
        xyzObj = dict()
        xyzObj['code'] = "P_SSID"
        xyzObj['system'] = "Link"
        xyz.append(xyzObj)
        abc = dict()
        abc['coding'] = xyz
        identifierObj['type'] = abc
        identifierObj['use'] = "usual"
        identifierObj['value'] = instance.p_ssid
        identifier.append(identifierObj)

        naming = list()
        nameobj = dict()
        eachlist = list()
        nameobj["use"] = "casual"
        eachlist.append(instance.f_name_eng)
        eachlist.append(instance.m_name_eng)
        eachlist.append(instance.l_name_eng)
        nameobj["given"] = eachlist
        naming.append(nameobj)

        telecom = list()
        telObj = dict()
        telObj["system"] = instance.alert_source
        telObj["use"] = "home"
        telObj["value"] = instance.alert_source_val
        telecom.append(telObj)

        representation = {
            "resourceType" : "Patient",
            "identifier" : identifier,
            "active" : "true",
            "name" : naming,
            "telecom" : telecom,
            "gender" : instance.Gender,
            "birthDate" : instance.dob,
            "deceasedBoolean" : "null",
            # "deceasedDateTime" : ,
            # "address" : 

        }

        return representation

class BankSerializer(serializers.ModelSerializer):
    # branches = BankBranchSerializer(many=True)
    class Meta:
        model = Bank
        fields = '__all__'

class BankBranchSerializer(serializers.ModelSerializer):
    Bank = BankSerializer(many=False)
    class Meta:
        model = BankBranch
        fields = '__all__'

class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthFacility
        fields = '__all__'

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'

class DiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diagnosis
        fields = '__all__'

class ClaimRecommendSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClaimRecommend
        fields = '__all__'
# To post claim payment status in IMIS from SOSYS
class ClaimSerializer(serializers.Serializer):
    claimId = serializers.CharField(max_length=60)
    paymentStatus = serializers.IntegerField()
    # action status update date
    paymentDate = serializers.CharField()
    paymentRemarks = serializers.CharField(default="")
    success = serializers.BooleanField(default=False)
    error = serializers.CharField(default=' ')

    def validate_paymentStatus(self,value):
        if value != 1 and value != 2:
            raise serializers.ValidationError('Invalid Status')
        return value
class ClaimDocumentsMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClaimDocumentsMaster
        exclude = ('UseBy','EnterDate' )