export function Login() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-md px-10 py-12 flex flex-col items-center gap-6 max-w-sm w-full">
        <h1 className="text-2xl font-bold font-mono text-gray-900">Lingo</h1>
        <p className="text-sm text-gray-500 text-center">
          Sign in to access your company glossary.
        </p>
        <button
          onClick={() => {
            window.location.href = '/auth/slack/login'
          }}
          className="flex items-center gap-3 bg-[#4A154B] hover:bg-[#3d1140] text-white font-semibold px-6 py-3 rounded-lg transition-colors w-full justify-center"
          aria-label="Sign in with Slack"
        >
          {/* Official Slack four-color pinwheel SVG mark */}
          <svg
            aria-hidden="true"
            width="20"
            height="20"
            viewBox="0 0 122.8 122.8"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path d="M25.8 77.6c0 7.1-5.8 12.9-12.9 12.9S0 84.7 0 77.6s5.8-12.9 12.9-12.9h12.9v12.9z" fill="#e01e5a" />
            <path d="M32.3 77.6c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9v32.3c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V77.6z" fill="#e01e5a" />
            <path d="M45.2 25.8c-7.1 0-12.9-5.8-12.9-12.9S38.1 0 45.2 0s12.9 5.8 12.9 12.9v12.9H45.2z" fill="#36c5f0" />
            <path d="M45.2 32.3c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H12.9C5.8 58.1 0 52.3 0 45.2s5.8-12.9 12.9-12.9H45.2z" fill="#36c5f0" />
            <path d="M97 45.2c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9-5.8 12.9-12.9 12.9H97V45.2z" fill="#2eb67d" />
            <path d="M90.5 45.2c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V12.9C64.7 5.8 70.5 0 77.6 0s12.9 5.8 12.9 12.9V45.2z" fill="#2eb67d" />
            <path d="M77.6 97c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9-12.9-5.8-12.9-12.9V97h12.9z" fill="#ecb22e" />
            <path d="M77.6 90.5c-7.1 0-12.9-5.8-12.9-12.9s5.8-12.9 12.9-12.9h32.3c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H77.6z" fill="#ecb22e" />
          </svg>
          Sign in with Slack
        </button>
      </div>
    </div>
  )
}
