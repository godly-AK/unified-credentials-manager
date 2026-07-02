import 'dart:convert';
import 'package:auth_app/rejection.dart';
import 'package:biometric_signature/biometric_signature.dart';
import 'package:biometric_signature/signature_options.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'dart:async';
import 'dart:io';
import 'package:http/http.dart' as http;

// class ChallengeException implements Exception {
//   final String message;

//   ChallengeException(this.message);

//   @override
//   String toString() => 'ChallengeException: $message';
// }

// /// A custom exception to represent errors that occur during the signature verification process.
// class VerificationException implements Exception {
//   final String message;

//   VerificationException(this.message);

//   @override
//   String toString() => 'VerificationException: $message';
// }

// Future<bool> verifySignature({
//   required String username,
//   required String challenge,
//   required String baseUrl,
//   required String signatureBase64,
// }) async {

//   final Uri url = Uri.parse('$baseUrl/verify');

//   final headers = {'Content-Type': 'application/json'};

//   final body = {
//     'username': username,
//     'challenge': challenge,
//     'signature': signatureBase64
//   };

//   final String encodedBody = jsonEncode(body);

//   try {
//     final response = await http.post(
//       url,
//       headers: headers,
//       body: encodedBody,
//     ).timeout(const Duration(seconds: 10));

//     final Map<String, dynamic> payload = jsonDecode(response.body);

//     if (response.statusCode == 200) {
//       final bool isVerified = payload['verified'] ?? false;

//       if (isVerified) {
//         return true;
//       } else {
//         final String errorMessage = payload['error'] ?? 'Unknown verification failure from server.';
//         throw VerificationException(errorMessage);
//       }
//     } else {
//       final String errorMessage = payload['error'] ?? 'Server returned error: ${response.statusCode}';
//       throw VerificationException(errorMessage);
//     }
//   } on TimeoutException {
//     throw VerificationException('The request timed out. Please check your network connection.');
//   } on SocketException {
//     throw VerificationException('Network error. Could not connect to the server.');
//   } catch (e) {
//     throw VerificationException('An unexpected error occurred: $e');
//   }
// }

class ForgotPasswordRequestException implements Exception {
  final String message;
  ForgotPasswordRequestException(this.message);

  @override
  String toString() => message;
}

Future<String> forgotPasswordRequest(String username, String baseUrl) async {
  final Uri requestUrl = Uri.parse('$baseUrl/api/forgot-password/request');
  try {
    final response = await http.post(
      requestUrl,
      headers: {'Content-Type': 'application/json; charset=UTF-8'},
      body: jsonEncode({'username': username}),
    );

    final responseBody = jsonDecode(response.body);

    if (response.statusCode == 200) {
      return responseBody['challenge'];
    } else {
      final errorMessage = responseBody['detail'] ?? 'Failed to get challenge.';
      throw Exception(errorMessage);
    }
  } catch (e) {
    throw ForgotPasswordRequestException(
      'An error occurred during forgot password request: $e',
    );
  }
}

Future<bool> forgotPasswordVerify(
  String username,
  String signedChallenge,
  String newPassword,
  String baseUrl,
) async {
  final Uri verifyUrl = Uri.parse('$baseUrl/api/forgot-password/verify');
  try {
    final response = await http.post(
      verifyUrl,
      headers: {'Content-Type': 'application/json; charset=UTF-8'},
      body: jsonEncode({
        'username': username,
        'signed_challenge': signedChallenge,
        'new_password': newPassword,
      }),
    );

    if (response.statusCode == 200) {
        final responseBody = jsonDecode(response.body);
        return responseBody['success'] == true;
      } else {
        // API returned an error (e.g., 401, 404)
        return false;
      }
  } catch (e) {
    ForgotPasswordRequestException(
      'An error occurred during forgot password verification: $e',
    );
    rethrow;
  }
}

// Future<String> fetchChallenge(String username, String baseUrl) async {
//   final Uri url = Uri.parse('$baseUrl/challenge/$username');

//   try {
//     final response = await http.get(url).timeout(const Duration(seconds: 10));

//     if (response.statusCode == 200) {
//       final Map<String, dynamic> payload = jsonDecode(response.body);
//       final String? challenge = payload['challenge'];
//       if (challenge != null && challenge.isNotEmpty) {
//         // SUCCESS: Return the challenge string
//         return challenge;
//       } else {
//         // ERROR: The server responded successfully but the data is invalid.
//         throw ChallengeException(
//           'Invalid payload from server: challenge is missing or empty.',
//         );
//       }
//     } else {
//       // ERROR: The server returned a non-200 status code (e.g., 404, 500).
//       throw ChallengeException(
//         'Server returned an error: ${response.statusCode}. Body: ${response.body}',
//       );
//     }
//   } on TimeoutException {
//     // ERROR: The request took too long.
//     throw ChallengeException(
//       'The request timed out. Please check your network connection.',
//     );
//   } on SocketException {
//     // ERROR: A network error occurred (e.g., no internet, DNS failure).
//     throw ChallengeException('Network error. Could not connect to the server.');
//   } catch (e) {
//     // ERROR: Catch-all for any other unexpected errors.
//     throw ChallengeException('An unexpected error occurred: $e');
//   }
// }

class Login extends StatelessWidget {
  Login({super.key});
  final biometricSignature = BiometricSignature();
  final usernameEditingController = TextEditingController();
  final passwordEditingController = TextEditingController();
  String payload = "";
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color.fromARGB(163, 29, 25, 75),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                "Change Password",
                textAlign: TextAlign.center,
                style: GoogleFonts.robotoMono(
                  color: const Color.fromARGB(255, 238, 141, 255),
                  fontSize: 30,
                  letterSpacing: 10,
                ),
              ),
              SizedBox(height: 20),
              Text(
                "Username",
                style: GoogleFonts.robotoMono(
                  color: const Color.fromARGB(255, 238, 141, 255),
                  fontSize: 16,
                ),
              ),
              SizedBox(height: 10),
              TextField(
                style: TextStyle(color: Color.fromARGB(255, 238, 141, 255)),
                controller: usernameEditingController,
                decoration: InputDecoration(
                  enabledBorder: OutlineInputBorder(
                    borderSide: BorderSide(color: Colors.green),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderSide: BorderSide(color: Colors.green),
                  ),
                  hint: Text(
                    "Your Username",
                    style: GoogleFonts.robotoMono(
                      color: const Color.fromARGB(67, 238, 141, 255),
                      fontSize: 16,
                    ),
                  ),
                ),
              ),
              SizedBox(height: 10),
              Text(
                "Password",
                style: GoogleFonts.robotoMono(
                  color: const Color.fromARGB(255, 229, 136, 246),
                  fontSize: 16,
                ),
              ),
              SizedBox(height: 10),
              TextField(
                controller: passwordEditingController,
                style: TextStyle(color: Color.fromARGB(255, 238, 141, 255)),
                decoration: InputDecoration(
                  enabledBorder: OutlineInputBorder(
                    borderSide: BorderSide(color: Colors.green),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderSide: BorderSide(color: Colors.green),
                  ),
                  hint: Text(
                    "Your Password",
                    style: GoogleFonts.robotoMono(
                      color: const Color.fromARGB(67, 238, 141, 255),
                      fontSize: 16,
                    ),
                  ),
                ),
              ),
              SizedBox(height: 10),
              ElevatedButton(
                onPressed: () async {
                  try {
                    payload = await forgotPasswordRequest(
                      usernameEditingController.text.trim(),
                      'https://heterostyled-charitably-raelynn.ngrok-free.dev',
                    );
                    final signature = await biometricSignature.createSignature(
                      SignatureOptions(payload: payload),
                    );
                    final verified = await forgotPasswordVerify(
                            usernameEditingController.text.trim(),
                            signature!,
                            passwordEditingController.text.trim(),
                            'https://heterostyled-charitably-raelynn.ngrok-free.dev',
                          );
                    if(verified){
                      Navigator.push(context, MaterialPageRoute(builder: (context)=>Rejection()));
                    }
                    else{
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Couldn't authenticate")));
                    }
                  } catch (e) {
                    ScaffoldMessenger.of(
                      context,
                    ).showSnackBar(SnackBar(content: Text(e.toString())));
                  }
                },
                style: ElevatedButton.styleFrom(
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(6),
                  ),
                  backgroundColor: Colors.green,
                ),
                child: SizedBox(
                  width: double.infinity,
                  child: Text(
                    "Change it!",
                    textAlign: TextAlign.center,
                    style: GoogleFonts.robotoMono(
                      color: const Color.fromARGB(255, 90, 30, 99),
                      fontSize: 16,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
