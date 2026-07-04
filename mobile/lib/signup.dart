import 'dart:convert';
import 'package:auth_app/acceptance.dart';
import 'package:biometric_signature/biometric_signature.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;

class Signup extends StatelessWidget {
  Signup({super.key});
  final biometricSignature = BiometricSignature();
  final usernameEditingController = TextEditingController();
  final passwordEditingController = TextEditingController();
  String msg = "";

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
                "Register key",
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
                style: TextStyle(color: Colors.white),
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
                obscureText: true,
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
                style: TextStyle(color: Colors.white),
              ),
              SizedBox(height: 10),
              ElevatedButton(
                onPressed: () async {
                  final key = await biometricSignature.createKeys();
                  if (key != null) {
                    final data = {
                      "username" : usernameEditingController.text.trim(),
                      "password" : passwordEditingController.text.trim(),
                      "public_key" : "-----BEGIN PUBLIC KEY-----\n$key\n-----END PUBLIC KEY-----"
                    };
                    try {
                      final response = await http.post(
                        Uri.parse("https://heterostyled-charitably-raelynn.ngrok-free.dev/login/android"),
                        headers: {"Content-Type": "application/json"},
                        body: jsonEncode(data),
                      );
                      final responseBody = jsonDecode(response.body);
                      if(response.statusCode == 200){
                        if (responseBody['success'] == true){
                          print(responseBody.toString());
                          Navigator.pop(context);
                          Navigator.push(context, MaterialPageRoute(builder: (context)=> Acceptance()));
                        }else{
                          biometricSignature.deleteKeys();
                          throw Exception('Login failed: ${responseBody['error'] ?? 'Unknown error'}');
                        }
                      }
                      
                    } catch (e) {
                      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
                    }
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
                    "Register",
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
