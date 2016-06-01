import jsonpickle

from cloudshell.cp.aws.domain.ami_management.operations.delete_operation import DeleteAMIOperation
from cloudshell.cp.aws.domain.ami_management.operations.deploy_operation import DeployAMIOperation

from cloudshell.cp.aws.common.driver_helper import CloudshellDriverHelper
from cloudshell.cp.aws.device_access_layer.aws_api import AWSApi
from cloudshell.cp.aws.domain.ami_management.operations.power_operation import PowerOperation
from cloudshell.cp.aws.domain.services.model_parser.aws_model_parser import AWSModelsParser
from cloudshell.cp.aws.domain.services.security_group_services.security_group_service import SecurityGroupService
from cloudshell.cp.aws.domain.services.session_providers.aws_session_provider import AWSSessionProvider
from cloudshell.cp.aws.domain.services.storage_services.ec2_storage_service import EC2StorageService
from cloudshell.cp.aws.domain.services.task_manager.instance_waiter import EC2InstanceWaiter
from cloudshell.cp.aws.models.deploy_result_model import DeployResult


class AWSShell(object):
    def __init__(self):
        self.aws_api = AWSApi()
        self.ec2_instance_waiter = EC2InstanceWaiter()
        self.ec2_storage_service = EC2StorageService()
        self.security_group_service = SecurityGroupService()
        self.model_parser = AWSModelsParser()
        self.cloudshell_session_helper = CloudshellDriverHelper()
        self.aws_session_manager = AWSSessionProvider()
        self.deploy_ami_operation = DeployAMIOperation(self.aws_api)
        self.power_management_operation = PowerOperation(self.aws_api, self.ec2_instance_waiter)
        self.delete_ami_operation = DeleteAMIOperation(self.aws_api,
                                                       self.ec2_instance_waiter,
                                                       self.ec2_storage_service,
                                                       self.security_group_service)

    def deploy_ami(self, command_context, deployment_request):
        """
        Will deploy Amazon Image on the cloud provider
        """
        aws_ami_deployment_model, name = self.model_parser.convert_to_deployment_resource_model(deployment_request)
        aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
        cloudshell_session = self.cloudshell_session_helper.get_session(command_context.connectivity.server_address,
                                                                        command_context.connectivity.admin_auth_token,
                                                                        command_context.reservation.domain)
        ec2_session = self.aws_session_manager.get_ec2_session(cloudshell_session, aws_ec2_resource_model)
        reservation_id = command_context.reservation.reservation_id

        result, name = self.deploy_ami_operation.deploy(ec2_session=ec2_session,
                                                        name=name,
                                                        reservation_id=reservation_id,
                                                        aws_ec2_cp_resource_model=aws_ec2_resource_model,
                                                        ami_deployment_model=aws_ami_deployment_model)
        deploy_data = DeployResult(vm_name=name,
                                   vm_uuid=result.instance_id,
                                   cloud_provider_resource_name=aws_ami_deployment_model.aws_ec2,
                                   auto_power_on=aws_ami_deployment_model.auto_power_on,
                                   auto_power_off=aws_ami_deployment_model.auto_power_off,
                                   wait_for_ip=aws_ami_deployment_model.wait_for_ip,
                                   auto_delete=aws_ami_deployment_model.auto_delete,
                                   autoload=aws_ami_deployment_model.autoload)

        return self._set_command_result(deploy_data)

    def power_on_ami(self, command_context):
        """
        Will power on the ami
        :param command_context: RemoteCommandContext
        :return:
        """
        aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
        cloudshell_session = self.cloudshell_session_helper.get_session(command_context.connectivity.server_address,
                                                                        command_context.connectivity.admin_auth_token,
                                                                        command_context.remote_reservation.domain)
        ec2_session = self.aws_session_manager.get_ec2_session(cloudshell_session, aws_ec2_resource_model)

        resource = command_context.remote_endpoints[0]
        data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)
        result = self.power_management_operation.power_on(ec2_session, data_holder.vmdetails.uid)
        cloudshell_session.SetResourceLiveStatus(resource.fullname, "Online", "Active")
        return self._set_command_result(result)

    def power_off_ami(self, command_context):
        """
        Will power on the ami
        :param command_context: RemoteCommandContext
        :return:
        """
        aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
        cloudshell_session = self.cloudshell_session_helper.get_session(command_context.connectivity.server_address,
                                                                        command_context.connectivity.admin_auth_token,
                                                                        command_context.remote_reservation.domain)
        ec2_session = self.aws_session_manager.get_ec2_session(cloudshell_session, aws_ec2_resource_model)

        resource = command_context.remote_endpoints[0]
        data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)
        result = self.power_management_operation.power_off(ec2_session, data_holder.vmdetails.uid)
        cloudshell_session.SetResourceLiveStatus(resource.fullname, "Offline", "Powered Off")
        return self._set_command_result(result)

    def delete_ami(self, command_context):
        """
        Will delete the ami instance
        :param command_context: RemoteCommandContext
        :return:
        """
        aws_ec2_resource_model = self.model_parser.convert_to_aws_resource_model(command_context.resource)
        cloudshell_session = self.cloudshell_session_helper.get_session(command_context.connectivity.server_address,
                                                                        command_context.connectivity.admin_auth_token,
                                                                        command_context.remote_reservation.domain)
        ec2_session = self.aws_session_manager.get_ec2_session(cloudshell_session, aws_ec2_resource_model)

        resource = command_context.remote_endpoints[0]
        data_holder = self.model_parser.convert_app_resource_to_deployed_app(resource)
        result = self.delete_ami_operation.delete_instance(ec2_session, data_holder.vmdetails.uid)
        return self._set_command_result(result)

    @staticmethod
    def _set_command_result(result, unpicklable=False):
        """
        Serializes output as JSON and writes it to console output wrapped with special prefix and suffix
        :param result: Result to return
        :param unpicklable: If True adds JSON can be deserialized as real object.
                            When False will be deserialized as dictionary
        """
        json = jsonpickle.encode(result, unpicklable=unpicklable)
        result_for_output = str(json)
        return result_for_output
