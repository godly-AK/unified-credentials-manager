import '../styles/globals.css';
import NavbarWrapper from '../Components/NavbarWrapper';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <title>NET KNIGHTS</title>
        <meta charSet="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Barriecito&family=Bitcount+Ink:wght@100..900&family=Bitcount+Single+Ink:wght@100..900&family=Fascinate&display=swaphttps://fonts.googleapis.com/css2?family=Barriecito&family=Fascinate&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-bitcount bg-gray-900 text-gray-100 text-center">
        <NavbarWrapper />
        <div className="pt-24 max-w-6xl mx-auto px-4">{children}</div>
      </body>
    </html>
  );
}
