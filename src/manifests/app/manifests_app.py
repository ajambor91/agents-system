from manifests.app.helpers.manifest_validator import ManifestValidator

class ManifestsApp:
    """Represents the manifests application."""

    def validate_manifest(self, manifest_data): 
        try: 
            return ManifestValidator.validate(manifest_data)
        except Exception as exc:
            raise exc