import MemberGenerateScreen from './components/MemberGenerateScreen.jsx'
import VerifierScreen from './components/VerifierScreen.jsx'

export default function App() {
  const pathname = typeof window !== 'undefined' ? window.location.pathname : '/'
  if (pathname === '/v') return <VerifierScreen />
  return <MemberGenerateScreen />
}
