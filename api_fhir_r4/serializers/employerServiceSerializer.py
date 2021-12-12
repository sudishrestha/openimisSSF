import copy

from insuree.models import Insuree

from api_fhir_r4.converters import EmployerServiceConverter,EmployeeeServiceConverter
from api_fhir_r4.serializers import BaseFHIRSerializer


class EmployeeeServiceSerializer (BaseFHIRSerializer):
    fhirConverter = EmployeeeServiceConverter ()

    def create(self, validated_data):
        copied_data = copy.deepcopy(validated_data)
        del copied_data['_state']
        return Insuree.objects.create(**copied_data)

    def update(self, instance, validated_data):
        # TODO legalForm isn't covered because that value is missing in the model
        # TODO LocationId isn't covered because that value is missing in the model
        # TODO offline isn't covered in the current version of API
        # TODO care_type isn't covered in the current version of API
        instance.other_names = validated_data.get('other_names', instance.other_names)
        instance.last_name = validated_data.get('name', instance.last_name)
        instance.chf_id = validated_data.get('chf_id', instance.chf_id)
        instance.save()
        return instance
class EmployerServiceSerializer (BaseFHIRSerializer):
    fhirConverter = EmployerServiceConverter()

    # def create(self, validated_data):
    #     copied_data = copy.deepcopy(validated_data)
    #     del copied_data['_state']
    #     return Insuree.objects.create(**copied_data)

    def update(self, instance, validated_data):
        # TODO legalForm isn't covered because that value is missing in the model
        # TODO LocationId isn't covered because that value is missing in the model
        # TODO offline isn't covered in the current version of API
        # TODO care_type isn't covered in the current version of API
        instance.E_SSID = validated_data.get('E_SSID', instance.E_SSID)
        instance.EmployerNameEng = validated_data.get('EmployerNameEng', instance.EmployerNameEng)
        instance.AddressId = validated_data.get('AddressId', instance.AddressId)
        instance.save()
        return instance