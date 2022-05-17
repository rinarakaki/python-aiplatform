# -*- coding: utf-8 -*-

# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import tempfile
import uuid

import pytest

from google.cloud import aiplatform
from google.cloud import storage

from tests.system.aiplatform import e2e_base


_XGBOOST_MODEL_URI = "gs://cloud-samples-data-us-central1/vertex-ai/google-cloud-aiplatform-ci-artifacts/models/iris_xgboost/model.bst"


@pytest.mark.usefixtures("delete_staging_bucket")
class TestVersionManagement(e2e_base.TestEndToEnd):

    _temp_prefix = "temp_vertex_sdk_e2e_model_upload_test"

    def test_upload_and_deploy_xgboost_model(self, shared_state):
        """Upload XGBoost model from local file and deploy it for prediction. Additionally, update model name, description and labels"""

        aiplatform.init(
            project=e2e_base._PROJECT,
            location=e2e_base._LOCATION,
        )

        storage_client = storage.Client(project=e2e_base._PROJECT)
        model_blob = storage.Blob.from_string(
            uri=_XGBOOST_MODEL_URI, client=storage_client
        )
        model_path = tempfile.mktemp() + ".my_model.xgb"
        model_blob.download_to_filename(filename=model_path)

        model_id = 'my_model_id' + uuid.uuid4().hex
        version_description = "My description"
        version_aliases = ['system-test-model', 'testing']

        model = aiplatform.Model.upload_xgboost_model_file(
            model_file_path=model_path,
            version_aliases=version_aliases,
            model_id=model_id,
            version_description=version_description
        )
        shared_state["resources"] = [model]

        staging_bucket = storage.Blob.from_string(
            uri=model.uri, client=storage_client
        ).bucket
        # Checking that the bucket is auto-generated
        assert "-vertex-staging-" in staging_bucket.name

        shared_state["bucket"] = staging_bucket

        assert model.version_description == version_description
        assert model.version_aliases == version_aliases
        assert 'default' in model.version_aliases

        # Currently we need to explicitly specify machine type.
        # See https://github.com/googleapis/python-aiplatform/issues/773
        endpoint = model.deploy(machine_type="n1-standard-2")
        shared_state["resources"].append(endpoint)
        predict_response = endpoint.predict(instances=[[0, 0, 0]])

        assert len(predict_response.predictions) == 1
        assert predict_response.model_version_id == '1'

        model2 = aiplatform.Model.upload_xgboost_model_file(
            model_file_path=model_path,
            parent_model=model_id,
            is_default_version=False
        )
        shared_state["resources"].append(model2)

        assert model2.version_id == '2'
        assert model2.resource_name == model.resource_name
        assert model2.version_aliases == []
        

