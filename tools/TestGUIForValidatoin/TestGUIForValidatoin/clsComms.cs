using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Text;
using System.IO;
using System.Reflection;
using System.Collections.Generic;

namespace TestGUIForValidatoin
{

    // State object for receiving data from remote device.
    public class StateObject
    {
        public Socket workSocket = null;                    // Client socket.
        public const int BufferSize = 256;                  // Size of receive buffer.
        public byte[] buffer = new byte[BufferSize];        // Receive buffer.
        public StringBuilder sb = new StringBuilder();      // Received data string.
    }

    public class AsynchronousClient
    {
        #region Module Variables
            private const int port = 1111;                     // The port number for the remote device.
            
            // ManualResetEvent instances signal completion.
            private static ManualResetEvent connectDone = new ManualResetEvent(false);
            private static ManualResetEvent sendDone = new ManualResetEvent(false);
            private static ManualResetEvent receiveDone = new ManualResetEvent(false);

            private static String response = String.Empty;      // The response from the remote device.
            private Socket gsckClient;
            public bool bConnected;
            private Form1 myinstance;

        #endregion

        #region Setup and Init
            public string StartClient(IPAddress ipAddressIn, Form1 forminst)  //, clsTransform pclsTrans)
            {
            myinstance = forminst;
                try
                {
                    // Create a TCP/IP socket.
                    IPEndPoint remoteEP = new IPEndPoint(ipAddressIn, port);
                    gsckClient = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);

                    // Connect to the remote endpoint.
                    gsckClient.BeginConnect(remoteEP, new AsyncCallback(ConnectCallback), gsckClient);
                    System.Threading.Thread.Sleep(200);
                    connectDone.WaitOne(5000);
              
                    Receive(gsckClient);                // Receive the response from the remote device.

                //mclsTransform = pclsTrans;
                if (gsckClient.Connected == true)
                {
                    bConnected = true;
                    return "Connected to " + ipAddressIn.ToString() + ":" + port.ToString();
                }
                else
                {
                    bConnected = false;
                    return "Failed to connect";
                }
                }
                catch (Exception e)
                {
                    Console.WriteLine(e.ToString());
                    return "Connection failed.";
                }
            }

            private void ConnectCallback(IAsyncResult ar)
            {
                try
                {
                    Socket client = (Socket)ar.AsyncState;      // Retrieve the socket from the state object.
                    client.EndConnect(ar);                      // Complete the connection.
                    Console.WriteLine("Socket connected to {0}", client.RemoteEndPoint.ToString());
                    connectDone.Set();                          // Signal that the connection has been made.
                }
                catch (Exception e)
                {
                    Console.WriteLine(e.ToString());
                }
            }
        #endregion

        #region Receive Handling
        public void Receive(Socket client)
        {
            try
            {
                StateObject state = new StateObject();      // Create the state object.
                state.workSocket = client;

                // Begin receiving the data from the remote device.
                client.BeginReceive(state.buffer, 0, StateObject.BufferSize, 0, new AsyncCallback(ReceiveCallback), state);
            }
            catch (Exception e)
            {
                Console.WriteLine(e.ToString());
            }
             
        }

        private void ReceiveCallback(IAsyncResult ar)
            {
            
            try
                {
                    // Retrieve the state object and the client socket from the asynchronous state object.
                    StateObject state = (StateObject)ar.AsyncState;
                    Socket client = state.workSocket;

                    // Read data from the remote device.
                    int bytesRead = client.EndReceive(ar);
                

                if (bytesRead > 0)
                {
                    // There might be more data, so store the data received so far.
                    state.sb.Append(Encoding.ASCII.GetString(state.buffer, 0, bytesRead));

                    // Get the rest of the data.
                    client.BeginReceive(state.buffer, 0, StateObject.BufferSize, 0, new AsyncCallback(ReceiveCallback), state);

                    Console.WriteLine("Received from NAO: " + state.sb.ToString());
                    Receivehandler(state.sb.ToString());
                    //GenerateResponse(state.sb.ToString());
                    state.sb.Clear();
                }
                else
                {
                    // All the data has arrived; put it in response.
                    if (state.sb.Length > 1)
                    {
                        response = state.sb.ToString();
                    }
                    // Signal that all bytes have been received.
                    receiveDone.Set();
                }
            }
            catch (Exception e)
                {
                    Console.WriteLine(e.ToString());
                }
            
        }
        #endregion

        #region Send Handling
        public void Send(String data)
        {

            if(gsckClient!=null)
            if (gsckClient.Connected == true)
            {
                data=data + "#";
                Console.WriteLine("Sending: " + data);
                // Convert the string data to byte data using ASCII encoding.
                byte[] byteData = Encoding.ASCII.GetBytes(data);

                // Begin sending the data to the remote device.
                gsckClient.BeginSend(byteData, 0, byteData.Length, 0, new AsyncCallback(SendCallback), gsckClient);
            }
            else
                myinstance.Text = "Connection broke!";
        }

            private void SendCallback(IAsyncResult ar)
            {
                try
                {
                    Socket client = (Socket)ar.AsyncState;          // Retrieve the socket from the state object.

                    // Complete sending the data to the remote device.
                    int bytesSent = client.EndSend(ar);
                    Console.WriteLine("Sent {0} bytes to server.", bytesSent);

                    // Signal that all bytes have been sent.
                    sendDone.Set();
                }
                catch (Exception e)
                {
                    Console.WriteLine(e.ToString());
                }
            }
        #endregion

        #region Application Specific Responses
            public void Receivehandler(String sDataIn)
            {
                Console.WriteLine(sDataIn);
                String[] data = sDataIn.Replace("#", "").Split('|');
            }

            private void WriteDataToFile(String sMessage)
            {
                string sTime = DateTime.Now.ToString("yyyyMMddHHmmss");
                string sFilePath = Directory.GetCurrentDirectory() + "\\KinectLogs\\Interaction_" + sTime + ".txt";
                System.IO.StreamWriter file = new System.IO.StreamWriter(sFilePath);
                file.Close();
                
                string sToWrite = sTime + ", " + sMessage;
                    
                // using handles opening/closing efficiently; the true means append to file (we made it before loop)
                using (file = new System.IO.StreamWriter(sFilePath, true))
                {
                    file.WriteLine(sToWrite);
                }
            }
        #endregion

        public void CloseSocket()
        {
            bConnected = false;
            gsckClient.Shutdown(SocketShutdown.Both);
            gsckClient.Close();
            gsckClient = null;
        }
    }
}