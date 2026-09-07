import { useSetupStatus } from '../lib/api';

export default function DecryptionErrorBanner() {
    const { data: setupData, isLoading } = useSetupStatus();

    // Only show if system-status shows decryption issues and setup wizard should be shown
    if (isLoading || !setupData) {
        return null;
    }

    const validation = setupData.validation;
    if (validation?.decryption_ok === true) {
        return null;
    }

    // If decryption is failing but system isn't showing setup wizard, something is wrong
    // with the logic. Show banner anyway.
    const isUnreadable = validation?.decryption_errors > 0;
    const isMissingFields = validation?.missing_fields?.length > 0;
    const jwtNotSet = setupData.jwt_secret_status !== 'set';

    if (!isUnreadable && !isMissingFields && !jwtNotSet) {
        return null;
    }

    return (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mx-4 my-4 text-red-300 text-sm">
            <strong className="text-red-200 block mb-1">Configuration Issue Detected</strong>
            {isUnreadable && (
                <p className="mb-1">
                    ⚠️ <strong>Decryption failed:</strong> Your encrypted credentials (Telegram session, bot token) cannot be decrypted.
                    This usually happens when the encryption key changed (e.g., after a deploy).
                </p>
            )}
            {isMissingFields && (
                <p className="mb-1">
                    ⚠️ <strong>Missing configuration:</strong> {validation.missing_fields.join(', ')}
                </p>
            )}
            {jwtNotSet && (
                <p className="mb-1">
                    ⚠️ <strong>JWT_SECRET not set:</strong> Please set a secure JWT_SECRET in your environment variables or via the admin panel.
                </p>
            )}
            <p className="mt-2">
                Please run the setup wizard again to re-configure your credentials with the current encryption key.
            </p>
        </div>
    );
}
