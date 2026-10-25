import { SITE_CONTACT_EMAIL, SITE_OPERATOR_NAME } from '$app/env/private';

export const load = () => ({
	site: { operator: SITE_OPERATOR_NAME, email: SITE_CONTACT_EMAIL }
});
