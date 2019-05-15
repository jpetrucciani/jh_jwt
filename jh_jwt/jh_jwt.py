"""
jupyter jwt authentication class
"""
from jupyterhub.handlers import BaseHandler
from jupyterhub.auth import Authenticator
from jupyterhub.auth import LocalAuthenticator
from jupyterhub.utils import url_path_join
from tornado import gen, web
from traitlets import List, Unicode, Bool
from jose import jwt


class JSONWebTokenLoginHandler(BaseHandler):
    """basic jwt login handler"""

    def get(self):
        header_name = self.authenticator.header_name
        param_name = self.authenticator.param_name
        post_login_url = self.authenticator.post_login_url
        auth_header_content = self.request.headers.get(header_name, "")
        auth_cookie_content = self.get_cookie("XSRF-TOKEN", "")
        signing_certificate = self.authenticator.signing_certificate
        secret = self.authenticator.secret
        username_claim_field = self.authenticator.username_claim_field
        audience = self.authenticator.expected_audience
        tokenParam = self.get_argument(param_name, default=False)

        if auth_header_content and tokenParam:
            raise web.HTTPError(400)
        elif auth_header_content:
            # we should not see 'token' as first word in the AUTHORIZATION header
            # if we do it could mean someone coming in with a stale API token
            if auth_header_content.split()[0] != "bearer":
                raise web.HTTPError(403)
            token = auth_header_content.split()[1]
        elif auth_cookie_content:
            token = auth_cookie_content
        elif tokenParam:
            token = tokenParam
        else:
            raise web.HTTPError(401)

        if token and self.authenticator.logout_on_new_token:
            self.clear_login_cookie()

        claims = {}
        if secret:
            claims = self.verify_jwt_using_secret(token, secret)
        elif signing_certificate:
            claims = self.verify_jwt_with_claims(token, signing_certificate, audience)
        else:
            raise web.HTTPError(401)

        # check the claims
        for claim in self.authenticator.boolean_claims:
            if not claims.get(claim, False):
                raise web.HTTPError(401, "%s claim validation failed", claim)
        for claim in self.authenticator.boolean_negative_claims:
            if claims.get(claim, True):
                raise web.HTTPError(401, "%s claim validation failed", claim)

        username = self.retrieve_username(claims, username_claim_field)
        user = self.user_from_username(username)
        self.set_login_cookie(user)

        _url = url_path_join(self.hub.server.base_url, post_login_url)

        self.redirect(_url)

    @staticmethod
    def verify_jwt_with_claims(token, signing_certificate, audience):
        # If no audience is supplied then assume we're not verifying the audience field.
        if audience == "":
            opts = {"verify_aud": False}
        else:
            opts = {}
        with open(signing_certificate, "r") as rsa_public_key_file:
            return jwt.decode(
                token, rsa_public_key_file.read(), audience=audience, options=opts
            )

    @staticmethod
    def verify_jwt_using_secret(json_web_token, secret):
        # If no audience is supplied then assume we're not verifying the audience field.
        return jwt.decode(
            json_web_token, secret, algorithms=list(jwt.ALGORITHMS.SUPPORTED)
        )

    @staticmethod
    def retrieve_username(claims, username_claim_field):
        # retrieve the username from the claims
        username = claims[username_claim_field].replace("-", "")
        if "@" in username:
            # process username as if email, pull out string before '@' symbol
            return username.split("@")[0]

        else:
            # assume not username and return the user
            return username


class JSONWebTokenAuthenticator(Authenticator):
    """
    Accept the authenticated JSON Web Token from header.
    """

    signing_certificate = Unicode(
        config=True,
        help="""
        The public certificate of the private key used to sign the incoming JSON Web Tokens.

        Should be a path to an X509 PEM format certificate filesystem.
        """,
    )

    username_claim_field = Unicode(
        default_value="upn",
        config=True,
        help="""
        The field in the claims that contains the user name. It can be either a straight username,
        of an email/userPrincipalName.
        """,
    )

    post_login_url = Unicode(
        default_value="home",
        config=True,
        help="""
        Where to redirect the user after login
        """,
    )

    expected_audience = Unicode(
        default_value="",
        config=True,
        help="""HTTP header to inspect for the authenticated JSON Web Token.""",
    )

    header_name = Unicode(
        default_value="Authorization",
        config=True,
        help="""HTTP header to inspect for the authenticated JSON Web Token.""",
    )

    param_name = Unicode(
        config=True,
        default_value="access_token",
        help="""The name of the query parameter used to specify the JWT token""",
    )

    secret = Unicode(
        config=True,
        help="""
        Shared secret key for siging JWT token.

        If defined, it overrides any setting for signing_certificate
        """,
    )

    boolean_claims = List(
        config=True,
        help="""
        A list of JWT boolean claims that must be true to allow the authentication.
        Use it to validate that a claim has the True value.
        For example, 'jupyterhub_access' is set to true.
        """,
    )

    boolean_negative_claims = List(
        config=True,
        help="""
        A list of JWT boolean claims that must be false to allow the authentication.
        Use it to validate that a claim as the False value.
        For example 'restricted' claim should be false.
        """,
    )

    logout_on_new_token = Bool(
        default_value=False,
        config=True,
        help="determines whether we logout before applying a new token",
    )

    def get_handlers(self, app):
        return [(r"/login", JSONWebTokenLoginHandler)]

    @gen.coroutine
    def authenticate(self, *args):
        raise NotImplementedError()


class JSONWebTokenLocalAuthenticator(JSONWebTokenAuthenticator, LocalAuthenticator):
    """
    A version of JSONWebTokenAuthenticator that mixes in local system user creation
    """

    pass
