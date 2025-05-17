"""OAuth authentication router for MCP server."""

from fastapi import APIRouter, Request, Form, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse
from typing import Optional
from urllib.parse import urlencode, parse_qs

from basic_memory.mcp.server import auth_provider, auth_settings
from loguru import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/authorize")
async def authorize(
    request: Request,
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query(...),
    state: Optional[str] = Query(None),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
):
    """OAuth authorization endpoint.
    
    This endpoint is called by Claude when connecting to the MCP server.
    """
    if not auth_provider:
        raise HTTPException(status_code=501, detail="OAuth not configured")
    
    # Get client info
    client = await auth_provider.get_client(client_id)
    if not client:
        raise HTTPException(status_code=400, detail="Invalid client")
    
    # For the basic provider, we'll immediately redirect with a code
    # In production with Supabase, this would redirect to Supabase login
    from mcp.server.auth.provider import AuthorizationParams
    from pydantic import AnyHttpUrl
    
    params = AuthorizationParams(
        state=state,
        scopes=scope.split(" ") if scope else ["read", "write"],
        code_challenge=code_challenge or "",
        redirect_uri=AnyHttpUrl(redirect_uri),
        redirect_uri_provided_explicitly=True,
    )
    
    try:
        auth_url = await auth_provider.authorize(client, params)
        return RedirectResponse(url=auth_url, status_code=302)
    except Exception as e:
        logger.error(f"Authorization error: {e}")
        error_params = {"error": "server_error", "error_description": str(e)}
        if state:
            error_params["state"] = state
        error_url = f"{redirect_uri}?{urlencode(error_params)}"
        return RedirectResponse(url=error_url, status_code=302)


@router.post("/token")
async def token(
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    scope: Optional[str] = Form(None),
):
    """OAuth token endpoint.
    
    Exchanges authorization code or refresh token for access token.
    """
    if not auth_provider:
        raise HTTPException(status_code=501, detail="OAuth not configured")
    
    # Get client
    client = await auth_provider.get_client(client_id)
    if not client:
        raise HTTPException(status_code=400, detail="Invalid client")
    
    try:
        if grant_type == "authorization_code":
            # Exchange authorization code
            if not code:
                raise HTTPException(status_code=400, detail="Missing authorization code")
            
            auth_code = await auth_provider.load_authorization_code(client, code)
            if not auth_code:
                raise HTTPException(status_code=400, detail="Invalid authorization code")
            
            token_response = await auth_provider.exchange_authorization_code(client, auth_code)
            
        elif grant_type == "refresh_token":
            # Refresh access token
            if not refresh_token:
                raise HTTPException(status_code=400, detail="Missing refresh token")
            
            refresh_token_obj = await auth_provider.load_refresh_token(client, refresh_token)
            if not refresh_token_obj:
                raise HTTPException(status_code=400, detail="Invalid refresh token")
            
            scopes = scope.split(" ") if scope else []
            token_response = await auth_provider.exchange_refresh_token(
                client, refresh_token_obj, scopes
            )
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported grant type")
        
        return {
            "access_token": token_response.access_token,
            "token_type": token_response.token_type,
            "expires_in": token_response.expires_in,
            "refresh_token": token_response.refresh_token,
            "scope": token_response.scope,
        }
    
    except Exception as e:
        logger.error(f"Token exchange error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/callback")
async def callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
):
    """OAuth callback endpoint for external providers.
    
    Handles callbacks from Supabase, GitHub, Google, etc.
    """
    if error:
        # Handle error from provider
        logger.error(f"OAuth callback error: {error} - {error_description}")
        return JSONResponse(
            status_code=400,
            content={"error": error, "error_description": error_description}
        )
    
    if not code or not state:
        return JSONResponse(
            status_code=400,
            content={"error": "missing_parameters", "error_description": "Missing code or state"}
        )
    
    # For Supabase/external providers, handle the callback
    if hasattr(auth_provider, 'handle_supabase_callback'):
        try:
            redirect_url = await auth_provider.handle_supabase_callback(code, state)
            return RedirectResponse(url=redirect_url, status_code=302)
        except Exception as e:
            logger.error(f"Callback handling error: {e}")
            return JSONResponse(
                status_code=400,
                content={"error": "callback_error", "error_description": str(e)}
            )
    
    # For basic provider, just redirect back with the code
    return RedirectResponse(
        url=f"http://localhost:3000/callback?code={code}&state={state}",
        status_code=302
    )


@router.post("/revoke")
async def revoke_token(
    token: str = Form(...),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
):
    """OAuth token revocation endpoint."""
    if not auth_provider:
        raise HTTPException(status_code=501, detail="OAuth not configured")
    
    # Get client
    client = await auth_provider.get_client(client_id)
    if not client:
        # Per spec, don't report errors for invalid client on revocation
        return {"status": "ok"}
    
    # Load token and revoke it
    access_token = await auth_provider.load_access_token(token)
    if access_token:
        await auth_provider.revoke_token(access_token)
    
    return {"status": "ok"}


@router.get("/.well-known/oauth-authorization-server")
async def oauth_metadata():
    """OAuth server metadata endpoint.
    
    Returns OAuth server configuration for automatic discovery.
    """
    if not auth_settings:
        raise HTTPException(status_code=501, detail="OAuth not configured")
    
    issuer_url = str(auth_settings.issuer_url)
    
    return {
        "issuer": issuer_url,
        "authorization_endpoint": f"{issuer_url}/auth/authorize",
        "token_endpoint": f"{issuer_url}/auth/token",
        "revocation_endpoint": f"{issuer_url}/auth/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "scopes_supported": ["read", "write", "admin"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
    }