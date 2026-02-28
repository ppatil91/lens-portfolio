module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js"
  ],
  theme: {
    extend: {
      fontFamily: { sans: ['Inter', 'sans-serif'] },
      colors: {
          brandBase: '#0f0f0f',
          brandSidebar: '#141414',
          brandCard: '#1a1a1a',
          brandAccent: '#DDAA77',
          brandAccentHover: '#cda06d',
          brandBorder: '#232323'
      }
    }
  },
  plugins: [],
}
