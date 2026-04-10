/**
 * Environment variable validation for GhostProtocol frontend.
 *
 * The API key is now injected server-side by the Next.js API proxy
 * route and is never exposed to the browser.
 */

interface EnvConfig {
  apiUrl: string;
  environment: string;
}

function validateEnv(): EnvConfig {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const environment = process.env.NODE_ENV || "development";

  // Validate API URL
  if (!apiUrl) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not defined. Please set it in your .env.local file."
    );
  }

  // Validate API URL format
  try {
    new URL(apiUrl);
  } catch (error) {
    throw new Error(
      `NEXT_PUBLIC_API_URL is not a valid URL: ${apiUrl}`
    );
  }

  return {
    apiUrl,
    environment,
  };
}

// Validate on module load
export const env = validateEnv();

// Export individual values for convenience
export const API_URL = env.apiUrl;
export const ENVIRONMENT = env.environment;

// Helper to check if we're in production
export const isProduction = () => ENVIRONMENT === "production";
export const isDevelopment = () => ENVIRONMENT === "development";
