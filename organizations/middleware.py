from organizations.models.membership import OrganizationMember


class ActiveOrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
       

        request.active_org = None
        request.org_role = None   # 👈 ADD THIS

        if request.user.is_authenticated:
           

            memberships = OrganizationMember.objects.filter(
                user=request.user,
                is_active=True
            ).select_related("organization")

            

            # Prefer admin membership
            admin_membership = memberships.filter(role="org_admin").first()
          

            if admin_membership:
                request.active_org = admin_membership.organization
                request.org_role = admin_membership.role   # 👈 SET ROLE
            else:
                first = memberships.first()
             
                if first:
                    request.active_org = first.organization
                    request.org_role = first.role          # 👈 SET ROLE

     

        return self.get_response(request)
