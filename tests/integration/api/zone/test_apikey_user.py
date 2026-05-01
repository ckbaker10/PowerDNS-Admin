import json

from powerdnsadmin.lib.validators import validate_zone

class TestIntegrationApiZoneUserApiKey(object):

    def test_empty_get(
        self,
        initial_apikey_data,
        client,
        user_apikey_integration
    ):
        res = client.get(
            "/api/v1/servers/localhost/zones",
            headers=user_apikey_integration
        )
        data = res.get_json(force=True)
        assert res.status_code == 200
        assert data == []

    def test_create_zone(
        self,
        initial_apikey_data,
        client,
        zone_data,
        user_apikey_integration
    ):
        res = client.post(
            "/api/v1/servers/localhost/zones",
            headers=user_apikey_integration,
            data=json.dumps(zone_data),
            content_type="application/json"
        )
        data = res.get_json(force=True)
        data['rrsets'] = []

        validate_zone(data)
        assert res.status_code == 201

        zone_url_format = "/api/v1/servers/localhost/zones/{0}"
        zone_url = zone_url_format.format(zone_data['name'].rstrip("."))
        res = client.delete(
            zone_url,
            headers=user_apikey_integration
        )

        assert res.status_code == 204

    def test_get_multiple_zones(
        self,
        initial_apikey_data,
        client,
        zone_data,
        user_apikey_integration
    ):
        res = client.post(
            "/api/v1/servers/localhost/zones",
            headers=user_apikey_integration,
            data=json.dumps(zone_data),
            content_type="application/json"
        )
        data = res.get_json(force=True)
        data['rrsets'] = []

        validate_zone(data)
        assert res.status_code == 201

        res = client.get(
            "/api/v1/servers/localhost/zones",
            headers=user_apikey_integration
        )
        data = res.get_json(force=True)
        assert res.status_code == 200
        assert len(data) >= 1

        zone_url_format = "/api/v1/servers/localhost/zones/{0}"
        zone_url = zone_url_format.format(zone_data['name'].rstrip("."))
        res = client.delete(
            zone_url,
            headers=user_apikey_integration
        )

        assert res.status_code == 204

    def test_delete_zone(
        self,
        initial_apikey_data,
        client,
        zone_data,
        user_apikey_integration
    ):
        res = client.post(
            "/api/v1/servers/localhost/zones",
            headers=user_apikey_integration,
            data=json.dumps(zone_data),
            content_type="application/json"
        )
        data = res.get_json(force=True)
        data['rrsets'] = []

        validate_zone(data)
        assert res.status_code == 201

        zone_url_format = "/api/v1/servers/localhost/zones/{0}"
        zone_url = zone_url_format.format(zone_data['name'].rstrip("."))
        res = client.delete(
            zone_url,
            headers=user_apikey_integration
        )

        assert res.status_code == 204
