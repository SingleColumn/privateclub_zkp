import { QRCodeSVG } from 'qrcode.react'

export default function QrCard({ value }) {
  return (
    <div className="inline-flex items-center justify-center p-4 rounded-lg bg-white">
      <QRCodeSVG value={value || ' '} size={140} level="M" />
    </div>
  )
}
