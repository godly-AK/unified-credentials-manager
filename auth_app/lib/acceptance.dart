import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class Acceptance extends StatelessWidget {
  const Acceptance({super.key, this.message});
  final String? message;

  @override
  Widget build(BuildContext context) {
    return Scaffold(backgroundColor: const Color.fromARGB(163, 29, 25, 75), body: Center(child: Padding(
      padding: const EdgeInsets.all(20.0),
      child: Text(
                      "Successfully Registered Key! You can now close the app.",
                      style: GoogleFonts.robotoMono(
                        color: const Color.fromARGB(255, 229, 136, 246),
                        fontSize: 16,
                      ),
                      textAlign: TextAlign.center,
                    ),
    ),));
  }
}