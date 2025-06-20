-- Create refresh_tokens table
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    token VARCHAR NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Add index for faster token lookups
CREATE INDEX IF NOT EXISTS refresh_tokens_token_idx ON refresh_tokens(token);

-- Add index for user_id for faster user token lookups
CREATE INDEX IF NOT EXISTS refresh_tokens_user_id_idx ON refresh_tokens(user_id);

-- Comments
COMMENT ON TABLE refresh_tokens IS 'Stores refresh tokens used to obtain new access tokens';
COMMENT ON COLUMN refresh_tokens.token IS 'The actual refresh token string';
COMMENT ON COLUMN refresh_tokens.expires_at IS 'When the token expires';
COMMENT ON COLUMN refresh_tokens.revoked IS 'Whether the token has been explicitly revoked';
COMMENT ON COLUMN refresh_tokens.user_id IS 'The user who owns this token'; 