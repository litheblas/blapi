from django.contrib.auth.backends import ModelBackend

def make_permission_set(source):
    """Skapar ett set av Permissions i det format Django förväntar sig.
    Fritt efter django.contrib.auth.backends.ModelBackend.get_all_permissions """
    return set(["%s.%s" % (permission.content_type.app_label, permission.codename) for permission in source])


class BlasBackend(ModelBackend):

    # Ersätter Djangos egna get_all_permissions för att få med rättigheter från poster/sektioner
    def get_all_permissions(self, user_obj, obj=None):
        perms = super(BlasBackend, self).get_all_permissions(user_obj=user_obj, obj=obj)  # Hämtar rättigheter på vedertaget vis
        perms.update(make_permission_set(user_obj.get_assignment_permissions(obj)))
        return perms
